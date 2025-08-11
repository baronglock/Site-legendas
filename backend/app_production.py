"""
API de Produção com Supabase e Processamento Real
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys
from pathlib import Path
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional
import jwt
import threading

# Adicionar ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar database e serviços
from database import db
from services.audio_extractor import AudioExtractor
from services.translation_optimizer import translation_optimizer

# Verificar Whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_TYPE = "faster"
    print("✅ Usando faster-whisper")
except ImportError:
    try:
        import whisper
        WHISPER_TYPE = "openai"
        print("✅ Usando OpenAI Whisper")
    except ImportError:
        print("❌ ERRO: Nenhum Whisper instalado!")
        WHISPER_TYPE = None

# Importar SubtitleGenerator local
from typing import List, Dict
from datetime import timedelta
import json

class SubtitleGenerator:
    """Versão simplificada para produção"""
    def __init__(self):
        self.output_dir = Path("/tmp/subtitle-ai/subtitles")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_subtitles(self, segments: List[Dict], video_id: str, 
                          max_line_width: int = 42, 
                          max_line_count: int = 2) -> Dict[str, str]:
        """Gera arquivos de legenda em múltiplos formatos"""
        
        # Gera diferentes formatos
        srt_path = self._generate_srt(segments, video_id)
        vtt_path = self._generate_vtt(segments, video_id)
        json_path = self._save_json(segments, video_id)
        
        return {
            "srt": str(srt_path),
            "vtt": str(vtt_path),
            "json": str(json_path)
        }
    
    def _generate_srt(self, segments: List[Dict], video_id: str) -> Path:
        """Gera arquivo SRT"""
        srt_path = self.output_dir / f"{video_id}.srt"
        
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._format_time_srt(segment["start"])
                end_time = self._format_time_srt(segment["end"])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        
        return srt_path
    
    def _generate_vtt(self, segments: List[Dict], video_id: str) -> Path:
        """Gera arquivo WebVTT"""
        vtt_path = self.output_dir / f"{video_id}.vtt"
        
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            
            for segment in segments:
                start_time = self._format_time_vtt(segment["start"])
                end_time = self._format_time_vtt(segment["end"])
                
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        
        return vtt_path
    
    def _save_json(self, segments: List[Dict], video_id: str) -> Path:
        """Salva transcrição em JSON"""
        json_path = self.output_dir / f"{video_id}.json"
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        
        return json_path
    
    def _format_time_srt(self, seconds: float) -> str:
        """Formata tempo para SRT (00:00:00,000)"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")
    
    def _format_time_vtt(self, seconds: float) -> str:
        """Formata tempo para WebVTT (00:00:00.000)"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

app = FastAPI(title="Subtitle AI - Production API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção real, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações
TEMP_DIR = Path("/tmp/subtitle-ai")
TEMP_DIR.mkdir(exist_ok=True)
(TEMP_DIR / "audio").mkdir(exist_ok=True)
(TEMP_DIR / "jobs").mkdir(exist_ok=True)
(TEMP_DIR / "subtitles").mkdir(exist_ok=True)

JWT_SECRET = os.getenv("JWT_SECRET", "seu-secret-aqui-mudar-em-producao")

# Serviços
audio_extractor = AudioExtractor()
subtitle_generator = SubtitleGenerator()

# Cache do modelo Whisper
whisper_model = None

def get_whisper_model(model_size="small"):
    """Carrega o modelo Whisper (com cache)"""
    global whisper_model
    
    if whisper_model is None:
        print(f"📥 Carregando modelo Whisper {model_size}...")
        
        if WHISPER_TYPE == "faster":
            whisper_model = WhisperModel(
                model_size, 
                device="cpu",  # Mudar para "cuda" se tiver GPU
                compute_type="int8",
                download_root="/tmp/whisper-models"
            )
        elif WHISPER_TYPE == "openai":
            whisper_model = whisper.load_model(model_size)
        
        print(f"✅ Modelo {model_size} carregado!")
    
    return whisper_model

# Models
class UserRegister(BaseModel):
    email: str

class UserLogin(BaseModel):
    email: str

# Dependência de autenticação
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Verifica token JWT e retorna usuário"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token não fornecido")
    
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        user = await db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(401, "Usuário não encontrado")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except Exception as e:
        print(f"Erro auth: {e}")
        raise HTTPException(401, "Token inválido")

# ROTAS
@app.get("/")
def root():
    return {
        "status": "API de Produção funcionando!",
        "whisper": WHISPER_TYPE,
        "database": "Conectado"
    }

@app.post("/api/v1/auth/register")
async def register(data: UserRegister):
    """Registro de novo usuário"""
    user = await db.create_user(data.email)
    if not user:
        raise HTTPException(400, "Erro ao criar usuário ou email já existe")
    
    # Gerar token
    token = jwt.encode({
        "user_id": str(user['id']),
        "email": user['email'],
        "exp": (datetime.utcnow() + timedelta(days=7)).timestamp()
    }, JWT_SECRET)
    
    stats = await db.get_user_stats(user['id'])
    
    return {
        "access_token": token,
        "user": {
            "id": str(user['id']),
            "email": user['email'],
            "plan": user.get('current_plan', 'free'),
            "minutes_available": stats.get('minutes_available', 20)
        }
    }

@app.post("/api/v1/auth/login")
async def login(data: UserLogin):
    """Login de usuário existente"""
    user = await db.get_user_by_email(data.email)
    if not user:
        # Auto-criar usuário no login
        user = await db.create_user(data.email)
    
    token = jwt.encode({
        "user_id": str(user['id']),
        "email": user['email'],
        "exp": (datetime.utcnow() + timedelta(days=7)).timestamp()
    }, JWT_SECRET)
    
    stats = await db.get_user_stats(user['id'])
    
    return {
        "access_token": token,
        "user": {
            "id": str(user['id']),
            "email": user['email'],
            "plan": user.get('current_plan', 'free'),
            "minutes_available": stats.get('minutes_available', 20)
        }
    }

@app.get("/api/v1/auth/me")
async def get_me(user = Depends(get_current_user)):
    """Dados do usuário autenticado"""
    stats = await db.get_user_stats(user['id'])
    
    return {
        "id": str(user['id']),
        "email": user['email'],
        "plan": user.get('current_plan', 'free'),
        "usage": stats
    }

@app.post("/api/v1/subtitle/upload")
async def upload_video(
    file: UploadFile = File(...),
    source_language: str = Form("auto"),
    target_language: str = Form("pt"),
    translate: bool = Form(True),
    user = Depends(get_current_user)
):
    """Upload e processamento com verificação de créditos REAL"""
    
    print(f"\n{'='*50}")
    print(f"📤 UPLOAD RECEBIDO - PRODUÇÃO")
    print(f"{'='*50}")
    print(f"👤 Usuário: {user['email']}")
    print(f"📁 Arquivo: {file.filename}")
    print(f"📊 Tamanho: {file.size / 1024 / 1024:.2f} MB")
    
    # Validar arquivo
    allowed = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.mp3', '.wav', '.m4a']
    ext = Path(file.filename).suffix.lower()
    
    if ext not in allowed:
        raise HTTPException(400, f"Formato não suportado")
    
    # Criar job
    job_id = f"job_{int(time.time())}_{hashlib.md5(file.filename.encode()).hexdigest()[:8]}"
    
    # Salvar arquivo temporariamente
    job_dir = TEMP_DIR / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    file_path = job_dir / file.filename
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # OBTER DURAÇÃO REAL DO ARQUIVO
    duration_seconds = audio_extractor.get_media_duration(str(file_path))
    duration_minutes = max(1, round(duration_seconds / 60))

    
    print(f"⏱️ Duração real: {duration_seconds:.1f}s = {duration_minutes} minutos")
    
    # Verificar créditos com duração REAL
    if not await db.check_user_credits(user['id'], duration_minutes):
        # Remover arquivo se não tiver créditos
        file_path.unlink()
        raise HTTPException(402, f"Créditos insuficientes. Necessário: {duration_minutes} minutos")
    
    # Criar job no banco
    job_data = {
        "id": job_id,
        "user_id": user['id'],
        "filename": file.filename,
        "status": "processing",
        "file_size": file.size,
        "source_language": source_language,
        "target_language": target_language,
        "file_url": str(file_path),
        "audio_duration_seconds": int(duration_seconds),  # Salvar duração real
        "whisper_model": "small",
        "translation_model": "googletrans",
        "metadata": {
            "translate": translate,
            "duration_minutes": duration_minutes
        }
    }
    
    job = await db.create_job(job_data)
    if not job:
        raise HTTPException(500, "Erro ao criar job")
    
    # Processar em thread
    thread = threading.Thread(
        target=process_video_production,
        args=(job_id, str(file_path), source_language, translate, target_language, user['id'])
    )
    thread.start()
    
    return {
        "job_id": job_id,
        "status": "processing",
        "duration_minutes": duration_minutes,
        "message": f"Upload realizado! Processando {duration_minutes} minutos de conteúdo."
    }

def process_video_production(job_id: str, file_path: str, source_lang: str, translate: bool, target_lang: str, user_id: str):
    """Processamento real com Whisper e tradução"""
    import asyncio
    
    async def process():
        try:
            print(f"\n🎬 PROCESSANDO: {job_id}")
            start_time = time.time()
            
            # 1. Extrair áudio
            print("🎵 Extraindo áudio...")
            await db.update_job(job_id, {"status": "extracting_audio"})
            
            audio_result = audio_extractor.extract_audio(file_path, job_id)
            if not audio_result["success"]:
                raise Exception(f"Erro ao extrair áudio: {audio_result.get('error')}")
            
            audio_path = audio_result["audio_path"]
            

            if not Path(audio_path).exists():
                raise Exception(f"Arquivo de áudio não foi criado: {audio_path}")

            # Verificar tamanho
            audio_size = Path(audio_path).stat().st_size
            if audio_size < 1000:  # Menos de 1KB
                raise Exception(f"Arquivo de áudio muito pequeno: {audio_size} bytes")

            print(f"✅ Áudio extraído: {audio_path} ({audio_size / 1024 / 1024:.2f} MB)")

            # 2. Transcrever
            print("🎤 Transcrevendo com Whisper...")
            await db.update_job(job_id, {"status": "transcribing"})
            
            model = get_whisper_model("small")
            
            if WHISPER_TYPE == "faster":
                segments, info = model.transcribe(
                    audio_path,
                    language=None if source_lang == "auto" else source_lang,
                    beam_size=5
                )
                
                result_segments = []
                for seg in segments:
                    result_segments.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text.strip()
                    })
                
                detected_language = info.language
            else:
                result = model.transcribe(
                    audio_path,
                    language=None if source_lang == "auto" else source_lang
                )
                
                result_segments = []
                for seg in result["segments"]:
                    result_segments.append({
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip()
                    })
                
                detected_language = result.get("language", "unknown")
            
            print(f"✅ Transcrição concluída: {len(result_segments)} segmentos")
            
            # 3. Gerar legendas
            print("📄 Gerando arquivos...")
            await db.update_job(job_id, {"status": "generating_subtitles"})
            
            subtitle_paths = subtitle_generator.generate_subtitles(
                result_segments,
                job_id
            )
            
            # 4. Traduzir se necessário
            if translate and detected_language != target_lang:
                print(f"🌐 Traduzindo de {detected_language} para {target_lang}...")
                await db.update_job(job_id, {"status": "translating"})
                
                translation_success = translation_optimizer.translate_file_optimized(
                    job_id, 
                    target_lang
                )
                
                if translation_success:
                    subtitle_paths[f"srt_{target_lang}"] = f"/tmp/subtitle-ai/subtitles/{job_id}_{target_lang}.srt"
                    subtitle_paths[f"vtt_{target_lang}"] = f"/tmp/subtitle-ai/subtitles/{job_id}_{target_lang}.vtt"
            
            job = await db.get_job(job_id)
            duration_seconds = job.get('audio_duration_seconds', 60)
            duration_minutes = max(1, int(duration_seconds / 60) + (1 if duration_seconds % 60 > 0 else 0))
            
            # Atualizar uso com minutos REAIS
            await db.update_user_usage(user_id, duration_minutes, job_id)
            
            processing_time = time.time() - start_time  # ← ADICIONAR ESTA LINHA
            
            # 6. Atualizar job como completo
            await db.update_job(job_id, {
                "status": "completed",
                "audio_duration_seconds": duration_seconds if 'duration_seconds' in locals() else 60,
                "processing_time_seconds": processing_time,  # ← AGORA EXISTE
                "result_urls": {
                    "original": f"/api/v1/download/{job_id}/srt",
                    "vtt": f"/api/v1/download/{job_id}/vtt",
                    "json": f"/api/v1/download/{job_id}/json"
                },
                "metadata": {
                    "detected_language": detected_language,
                    "segments_count": len(result_segments),
                    "translated": translate
                }
            })
            
            # 7. Atualizar uso
            job = await db.get_job(job_id)
            duration_seconds = job.get('audio_duration_seconds', 60)
            duration_minutes = max(1, int(duration_seconds / 60) + (1 if duration_seconds % 60 > 0 else 0))
            
            await db.update_user_usage(user_id, duration_minutes, job_id)
            
            print(f"✅ JOB COMPLETO: {job_id}")
            print(f"⏱️ Duração do conteúdo: {duration_minutes} minutos")
            print(f"⚡ Tempo de processamento: {processing_time:.1f}s")  # ← AGORA FUNCIONA
            
        except Exception as e:
            print(f"❌ ERRO no job {job_id}: {e}")
            await db.update_job(job_id, {
                "status": "failed",
                "error": str(e)
            })
    
    # Executar
    asyncio.run(process())

@app.get("/api/v1/subtitle/job/{job_id}")
async def get_job_status(job_id: str):
    """Status do job (público para simplicidade)"""
    job = await db.get_job(job_id)
    
    if not job:
        raise HTTPException(404, "Job não encontrado")
    
    return job

@app.get("/api/v1/download/{job_id}/{format}")
async def download_file(job_id: str, format: str):
    """Download do arquivo"""
    
    # Verificar se é traduzido
    if "_pt" in job_id:
        base_job_id = job_id.replace("_pt", "")
        file_path = Path(f"/tmp/subtitle-ai/subtitles/{base_job_id}_pt.{format}")
    else:
        file_path = Path(f"/tmp/subtitle-ai/subtitles/{job_id}.{format}")
    
    if not file_path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    
    return FileResponse(
        path=file_path,
        filename=f"{job_id}.{format}",
        media_type="text/plain"
    )

@app.get("/api/v1/user/jobs")
async def get_user_jobs(
    limit: int = 20,
    offset: int = 0,
    user = Depends(get_current_user)
):
    """Lista jobs do usuário"""
    jobs = await db.get_user_jobs(user['id'], limit, offset)
    
    return {
        "jobs": jobs,
        "total": len(jobs),
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/user/usage")
async def get_usage(user = Depends(get_current_user)):
    """Uso do usuário"""
    stats = await db.get_user_stats(user['id'])
    
    return {
        "current_month": {
            "minutes_used": stats.get('minutes_used', 0),
            "minutes_limit": stats.get('minutes_limit', 20),
            "minutes_available": stats.get('minutes_available', 20)
        }
    }

@app.get("/api/v1/user/stats")
async def get_stats(user = Depends(get_current_user)):
    """Estatísticas completas"""
    return await db.get_user_stats(user['id'])

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 SERVIDOR DE PRODUÇÃO - SUBTITLE AI")
    print("="*60)
    print(f"✅ Whisper: {WHISPER_TYPE}")
    print(f"✅ Banco: Supabase conectado")
    print(f"✅ Auth: JWT")
    print(f"📁 Temp: {TEMP_DIR}")
    print(f"🌐 API: http://localhost:8000")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)