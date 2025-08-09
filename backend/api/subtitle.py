# backend/api/subtitle.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from typing import Optional
import os

from config import Config
from models.schemas import JobStatus, Language
from models.database import JobModel, UsageModel
from services.video_processor import VideoProcessor
from services.transcription import WhisperTranscriber
from services.translator_pro import AISubtitleTranslator
from services.subtitle_generator import SubtitleGenerator
from utils.queue_manager import QueueManager
from utils.r2_storage import R2Storage
from utils.validators import Validators
from utils.rate_limiter import RateLimiter
from api.auth import get_current_user

router = APIRouter(prefix="/subtitle", tags=["Subtitles"])

# Inicializa serviços
video_processor = VideoProcessor()
subtitle_generator = SubtitleGenerator()
queue_manager = QueueManager()
r2_storage = R2Storage()
rate_limiter = RateLimiter()
job_model = JobModel()
usage_model = UsageModel()

# Cache de transcribers por modelo
transcribers = {}

def get_transcriber(model_name: str) -> WhisperTranscriber:
    """Obtém ou cria transcritor para o modelo especificado"""
    if model_name not in transcribers:
        transcribers[model_name] = WhisperTranscriber(model_name)
    return transcribers[model_name]

@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_language: Language = Language.AUTO,
    target_language: Optional[Language] = Language.PT,
    translate: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Upload de vídeo/áudio para transcrição
    """
    user_id = current_user['id']
    user_plan = current_user.get('current_plan', 'free')
    
    # Verifica rate limit
    allowed, info = rate_limiter.check_rate_limit(user_id, 'uploads', user_plan)
    if not allowed:
        raise HTTPException(
            status_code=429, 
            detail=f"Limite de uploads excedido. Disponível em {info['reset_in']} segundos"
        )
    
    # Valida arquivo
    max_size = Config.MAX_FILE_SIZE_MB_FREE if user_plan == 'free' else Config.MAX_FILE_SIZE_MB_PAID
    
    # Salva temporariamente para validar
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    valid, error = Validators.validate_file_upload(temp_path, max_size)
    if not valid:
        os.unlink(temp_path)
        raise HTTPException(status_code=400, detail=error)
    
    # Estima duração
    file_type = 'video' if any(file.filename.endswith(ext) for ext in Config.ALLOWED_VIDEO_EXTENSIONS) else 'audio'
    estimated_duration = Validators.estimate_duration_from_size(len(content), file_type) / 60  # minutos
    
    # Verifica créditos
    can_use, usage_info = usage_model.can_use(user_id, estimated_duration)
    if not can_use:
        os.unlink(temp_path)
        raise HTTPException(
            status_code=402, 
            detail=f"Créditos insuficientes. Disponível: {usage_info['available']:.1f} min, Necessário: {usage_info['requested']:.1f} min"
        )
    
    # Cria job
    job = job_model.create(user_id, file_type, source_language)
    job_id = job['id']
    
    # Processa upload
    with open(temp_path, 'rb') as f:
        process_result = video_processor.process_upload(
            f, 
            Validators.sanitize_filename(file.filename),
            user_id
        )
    
    os.unlink(temp_path)
    
    if not process_result['success']:
        job_model.update_status(job_id, 'failed', process_result.get('error'))
        raise HTTPException(status_code=500, detail=process_result.get('error'))
    
    # Atualiza job com informações do áudio
    job_model.update_job_details(
        job_id,
        r2_audio_key=process_result['audio_key'],
        audio_duration_seconds=int(process_result.get('duration', estimated_duration * 60))
    )
    
    # Adiciona à fila
    queue_data = {
        'job_id': job_id,
        'user_id': user_id,
        'user_plan': user_plan,
        'audio_url': process_result['audio_url'],
        'source_language': source_language,
        'target_language': target_language if translate else None,
        'translate': translate,
        'duration_minutes': process_result.get('duration', estimated_duration * 60) / 60
    }
    
    queue_manager.add_job(queue_data, user_plan)
    
    # Agenda processamento em background
    background_tasks.add_task(process_subtitle_job, queue_data)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "estimated_duration": f"{estimated_duration:.1f} minutos",
        "position_in_queue": queue_manager.get_job_position(job_id),
        "estimated_wait_time": queue_manager.get_estimated_wait_time(
            'free' if user_plan == 'free' else 'paid'
        )
    }

@router.post("/url")
async def process_url(
    background_tasks: BackgroundTasks,
    url: str,
    source_language: Language = Language.AUTO,
    target_language: Optional[Language] = Language.PT,
    translate: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Processa vídeo de URL
    """
    user_id = current_user['id']
    user_plan = current_user.get('current_plan', 'free')
    
    # Valida URL
    valid, platform = Validators.is_valid_url(url)
    if not valid:
        raise HTTPException(status_code=400, detail="URL inválida")
    
    # Verifica rate limit
    allowed, info = rate_limiter.check_rate_limit(user_id, 'uploads', user_plan)
    if not allowed:
        raise HTTPException(
            status_code=429, 
            detail=f"Limite excedido. Disponível em {info['reset_in']} segundos"
        )
    
    # Cria job
    job = job_model.create(user_id, 'url', source_language)
    job_id = job['id']
    
    # Processa URL
    process_result = video_processor.process_url(url, user_id)
    
    if not process_result['success']:
        job_model.update_status(job_id, 'failed', process_result.get('error'))
        raise HTTPException(status_code=500, detail=process_result.get('error'))
    
    # Estima duração
    duration_minutes = process_result.get('duration', 0) / 60
    
    # Verifica créditos
    can_use, usage_info = usage_model.can_use(user_id, duration_minutes)
    if not can_use:
        job_model.update_status(job_id, 'failed', 'Créditos insuficientes')
        raise HTTPException(
            status_code=402, 
            detail=f"Créditos insuficientes. Disponível: {usage_info['available']:.1f} min"
        )
    
    # Atualiza job
    job_model.update_job_details(
        job_id,
        original_url=url,
        r2_audio_key=process_result['audio_key'],
        audio_duration_seconds=int(process_result.get('duration', 0))
    )
    
    # Adiciona à fila
    queue_data = {
        'job_id': job_id,
        'user_id': user_id,
        'user_plan': user_plan,
        'audio_url': process_result['audio_url'],
        'source_language': source_language,
        'target_language': target_language if translate else None,
        'translate': translate,
        'duration_minutes': duration_minutes,
        'title': process_result.get('title', 'Unknown'),
        'platform': platform
    }
    
    queue_manager.add_job(queue_data, user_plan)
    
    # Agenda processamento
    background_tasks.add_task(process_subtitle_job, queue_data)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "title": process_result.get('title', 'Unknown'),
        "platform": platform,
        "duration": f"{duration_minutes:.1f} minutos",
        "position_in_queue": queue_manager.get_job_position(job_id),
        "estimated_wait_time": queue_manager.get_estimated_wait_time(
            'free' if user_plan == 'free' else 'paid'
        )
    }

@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verifica status do job
    """
    job = job_model.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    if job['user_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    # Pega status da fila se ainda não completou
    if job['status'] in ['queued', 'processing']:
        queue_status = queue_manager.get_job_status(job_id)
        position = queue_manager.get_job_position(job_id)
        
        return {
            "job_id": job_id,
            "status": job['status'],
            "position_in_queue": position,
            "created_at": job['created_at'],
            "queue_status": queue_status
        }
    
    # Se completou, retorna URLs de download
    if job['status'] == 'completed':
        download_urls = {}
        
        # URL da legenda original
        if job.get('r2_subtitle_key'):
            download_urls['original'] = r2_storage.generate_download_url(
                job['r2_subtitle_key']
            )
        
        # URL da legenda traduzida
        if job.get('r2_translated_key'):
            download_urls['translated'] = r2_storage.generate_download_url(
                job['r2_translated_key']
            )
        
        return {
            "job_id": job_id,
            "status": "completed",
            "download_urls": download_urls,
            "source_language": job.get('source_language'),
            "target_language": job.get('target_language'),
            "duration_seconds": job.get('audio_duration_seconds'),
            "completed_at": job.get('completed_at')
        }
    
    # Se falhou
    return {
        "job_id": job_id,
        "status": job['status'],
        "error": job.get('error_message')
    }

@router.delete("/job/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancela job na fila
    """
    job = job_model.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    if job['user_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    if job['status'] not in ['queued']:
        raise HTTPException(status_code=400, detail="Job não pode ser cancelado")
    
    # Remove da fila
    if queue_manager.cancel_job(job_id):
        job_model.update_status(job_id, 'cancelled')
        return {"message": "Job cancelado com sucesso"}
    
    raise HTTPException(status_code=500, detail="Erro ao cancelar job")

async def process_subtitle_job(job_data: dict):
    """
    Processa job de legenda (roda em background)
    """
    job_id = job_data['job_id']
    user_id = job_data['user_id']
    user_plan = job_data['user_plan']
    
    try:
        # Atualiza status
        job_model.update_status(job_id, 'processing')
        
        # Define modelo baseado no plano
        whisper_model = Config.WHISPER_MODEL_FREE if user_plan == 'free' else Config.WHISPER_MODEL_PAID
        translation_model = Config.TRANSLATION_MODEL_FREE if user_plan == 'free' else Config.TRANSLATION_MODEL_PAID
        
        # 1. Download do áudio do R2 (implementar)
        # Por enquanto, vamos assumir que temos o arquivo local
        
        # 2. Transcrição
        job_model.update_status(job_id, 'transcribing')
        transcriber = get_transcriber(whisper_model)
        
        # Aqui você precisa baixar o áudio do R2 para um arquivo temporário
        # transcription_result = transcriber.transcribe(audio_path, job_data['source_language'])
        
        # 3. Geração de legendas
        # subtitle_paths = subtitle_generator.generate_subtitles(...)
        
        # 4. Tradução (se solicitado)
        if job_data.get('translate') and job_data.get('target_language'):
            job_model.update_status(job_id, 'translating')
            # translator = AISubtitleTranslator()
            # translated_segments = translator.translate_segments(...)
        
        # 5. Upload para R2
        # r2_result = r2_storage.upload_file(...)
        
        # 6. Atualiza job como completo
        job_model.update_status(job_id, 'completed')
        
        # 7. Consome créditos
        usage_model.consume_minutes(
            user_id, 
            job_data['duration_minutes'],
            job_data['duration_minutes'] if job_data.get('translate') else 0
        )
        
    except Exception as e:
        job_model.update_status(job_id, 'failed', str(e))
        print(f"Erro no job {job_id}: {e}")