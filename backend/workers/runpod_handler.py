# workers/runpod_handler.py
import runpod
import os
import json
import time
from typing import Dict, Any
import traceback

# Import dos processadores
from job_processor import JobProcessor

# Inicializa processador
processor = JobProcessor()

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler principal do RunPod
    
    Input esperado:
    {
        "input": {
            "job_id": "xxx",
            "user_id": "xxx", 
            "audio_url": "https://r2.url/audio.wav",
            "source_language": "auto",
            "target_language": "pt",
            "translate": true,
            "whisper_model": "base",
            "translation_model": "gpt-5-nano"
        }
    }
    """
    try:
        # Pega input do job
        job_input = job.get("input", {})
        job_id = job_input.get("job_id")
        
        if not job_id:
            return {"error": "job_id é obrigatório"}
        
        print(f"Processando job {job_id}")
        start_time = time.time()
        
        # Atualiza status para processing
        processor.update_job_status(job_id, "processing")
        
        # 1. Download do áudio
        print("Baixando áudio...")
        audio_path = processor.download_audio_from_r2(
            job_input["audio_url"],
            job_id
        )
        
        if not audio_path:
            raise Exception("Falha no download do áudio")
        
        # 2. Transcrição
        print(f"Transcrevendo com {job_input.get('whisper_model', 'base')}...")
        processor.update_job_status(job_id, "transcribing")
        
        transcription_result = processor.transcribe_audio(
            audio_path,
            job_input.get("source_language", "auto"),
            job_input.get("whisper_model", "base")
        )
        
        if not transcription_result["success"]:
            raise Exception(f"Erro na transcrição: {transcription_result.get('error')}")
        
        segments = transcription_result["segments"]
        detected_language = transcription_result["language"]
        
        # 3. Tradução (se solicitado)
        translated_segments = None
        if job_input.get("translate") and job_input.get("target_language"):
            if detected_language != job_input["target_language"]:
                print(f"Traduzindo de {detected_language} para {job_input['target_language']}...")
                processor.update_job_status(job_id, "translating")
                
                translated_segments = processor.translate_segments(
                    segments,
                    detected_language,
                    job_input["target_language"],
                    job_input.get("translation_model", "gpt-5-nano")
                )
        
        # 4. Gerar legendas
        print("Gerando arquivos de legenda...")
        processor.update_job_status(job_id, "generating")
        
        # Legendas originais
        subtitle_result = processor.generate_and_upload_subtitles(
            segments,
            job_id,
            job_input["user_id"],
            is_translated=False
        )
        
        if not subtitle_result["success"]:
            raise Exception("Erro ao gerar legendas")
        
        # Legendas traduzidas (se aplicável)
        translated_result = None
        if translated_segments:
            translated_result = processor.generate_and_upload_subtitles(
                translated_segments,
                f"{job_id}_translated",
                job_input["user_id"],
                is_translated=True
            )
        
        # 5. Atualiza job como completo
        job_data = {
            "status": "completed",
            "source_language": detected_language,
            "target_language": job_input.get("target_language"),
            "r2_subtitle_key": subtitle_result["keys"].get("srt"),
            "r2_subtitle_vtt_key": subtitle_result["keys"].get("vtt"),
            "r2_subtitle_json_key": subtitle_result["keys"].get("json"),
        }
        
        if translated_result:
            job_data["r2_translated_key"] = translated_result["keys"].get("srt")
            job_data["r2_translated_vtt_key"] = translated_result["keys"].get("vtt")
        
        processor.update_job_complete(job_id, job_data)
        
        # 6. Consome créditos do usuário
        audio_duration_minutes = transcription_result.get("duration", 0) / 60
        processor.consume_user_credits(
            job_input["user_id"],
            audio_duration_minutes,
            audio_duration_minutes if job_input.get("translate") else 0
        )
        
        # Limpa arquivo temporário
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "job_id": job_id,
            "processing_time": processing_time,
            "detected_language": detected_language,
            "was_translated": bool(translated_segments),
            "subtitle_urls": subtitle_result.get("urls", {}),
            "translated_urls": translated_result.get("urls", {}) if translated_result else {}
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Erro no job {job_id}: {error_msg}")
        print(traceback.format_exc())
        
        # Atualiza job como falho
        processor.update_job_status(
            job_input.get("job_id", "unknown"),
            "failed",
            error_msg
        )
        
        return {
            "error": error_msg,
            "job_id": job_input.get("job_id", "unknown")
        }

# RunPod handler
runpod.serverless.start({"handler": handler})