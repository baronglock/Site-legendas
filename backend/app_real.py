"""
Servidor REAL com transcrição Whisper funcionando
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil
from pathlib import Path
import hashlib
import time
import os
import sys
from googletrans import Translator
from services.translation_optimizer import translation_optimizer
import uvicorn



# Adicionar o backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Subtitle API - REAL")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar serviços REAIS
from services.audio_extractor import AudioExtractor

# SubtitleGenerator simplificado para teste local
from typing import List, Dict
from pathlib import Path
import json
from datetime import timedelta

class SubtitleGenerator:
    """Versão simplificada para teste local"""
    def __init__(self):
        self.output_dir = Path("/storage/legendas-master/temp/subtitles")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_subtitles(self, segments: List[Dict], video_id: str, 
                          max_line_width: int = 42, 
                          max_line_count: int = 2) -> Dict[str, str]:
        """
        Gera arquivos de legenda em múltiplos formatos
        """
        print(f"\n   📝 Gerando legendas para: {video_id}")
        print(f"   📊 Total de segmentos: {len(segments)}")
        
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

# Configurar caminhos
TEMP_DIR = Path("/storage/legendas-master/temp")
JOBS_DIR = TEMP_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Inicializar serviços
audio_extractor = AudioExtractor()
subtitle_generator = SubtitleGenerator()

# Verificar qual Whisper está disponível
try:
    from faster_whisper import WhisperModel
    WHISPER_TYPE = "faster"
    print("✅ Usando faster-whisper (mais eficiente)")
except ImportError:
    try:
        import whisper
        WHISPER_TYPE = "openai"
        print("✅ Usando OpenAI Whisper")
    except ImportError:
        print("❌ ERRO: Nenhum Whisper instalado!")
        WHISPER_TYPE = None

# Cache do modelo
whisper_model = None

def get_whisper_model(model_size="small"):
    """Carrega o modelo Whisper (com cache)"""
    global whisper_model
    
    if whisper_model is None:
        print(f"📥 Carregando modelo Whisper {model_size}...")
        
        if WHISPER_TYPE == "faster":
            whisper_model = WhisperModel(
                model_size, 
                device="cpu",
                compute_type="int8",
                download_root="/storage/legendas-master/models/whisper"
            )
        elif WHISPER_TYPE == "openai":
            whisper_model = whisper.load_model(model_size)
        else:
            raise Exception("Whisper não está instalado!")
        
        print(f"✅ Modelo {model_size} carregado!")
    
    return whisper_model

# Armazenar jobs
jobs_db = {}

class UserRegister(BaseModel):
    email: str

@app.get("/")
def root():
    return {
        "status": "API Real funcionando",
        "whisper": WHISPER_TYPE,
        "endpoints": {
            "upload": "/api/v1/subtitle/upload",
            "status": "/api/v1/subtitle/job/{job_id}",
            "download": "/api/v1/download/{job_id}/srt"
        }
    }

# AUTH MOCK
@app.post("/api/v1/auth/register")
async def register(user: UserRegister):
    return {
        "access_token": "real_token_123",
        "user_id": "user_123",
        "plan": "free",
        "minutes_available": 1000
    }

@app.post("/api/v1/auth/login")
async def login(user: UserRegister):
    return {
        "access_token": "real_token_123",
        "user_id": "user_123",
        "plan": "free",
        "minutes_available": 1000
    }

@app.get("/api/v1/auth/me")
async def me():
    return {
        "id": "user_123",
        "email": "test@test.com",
        "plan": "free",
        "usage": {
            "minutes_used": 10,
            "minutes_limit": 1000,
            "minutes_available": 990
        }
    }

# UPLOAD REAL
@app.post("/api/v1/subtitle/upload")
async def upload_video_real(
    file: UploadFile = File(...),
    source_language: str = Form("auto"),  # Adicionar Form
    target_language: str = Form("pt"),    # Adicionar Form
    translate: bool = Form(True)          # Adicionar Form
):
    """Upload e processamento REAL com Whisper"""
    
    # Adicionar no início dos imports:
    
    print(f"\n{'='*50}")
    print(f"📤 UPLOAD REAL RECEBIDO")
    print(f"{'='*50}")
    print(f"📁 Arquivo: {file.filename}")
    print(f"📊 Tamanho: {file.size / 1024 / 1024:.2f} MB")
    print(f"🎯 Tipo: {file.content_type}")
    print(f"🌐 Idioma origem: {source_language}")  # Adicionar
    print(f"🌐 Idioma destino: {target_language}")  # Adicionar
    print(f"🔄 Traduzir: {translate}")  # Adicionar

    # Validar
    allowed = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.mp3', '.wav', '.m4a', '.aac']
    ext = Path(file.filename).suffix.lower()
    
    if ext not in allowed:
        raise HTTPException(400, f"Formato não suportado. Use: {', '.join(allowed)}")
    
    # Criar job
    job_id = f"job_{int(time.time())}_{hashlib.md5(file.filename.encode()).hexdigest()[:6]}"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    # Salvar arquivo
    input_path = job_dir / file.filename
    print(f"💾 Salvando em: {input_path}")
    
    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Criar job
    jobs_db[job_id] = {
        "id": job_id,
        "status": "processing",
        "filename": file.filename,
        "created_at": time.time(),
        "progress": "Iniciando...",
        "source_language": source_language,  # Adicionar
        "target_language": target_language,  # Adicionar
        "translate": translate  # Adicionar
    }
    
    # Processar em thread separada
    import threading
    thread = threading.Thread(
        target=process_video_real,
        args=(job_id, str(input_path), source_language)
    )
    thread.start()
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Upload realizado! Processamento REAL iniciado.",
        "estimated_duration": "Depende do tamanho do arquivo"
    }

def process_video_real(job_id: str, input_path: str, source_language: str):
    """Processamento REAL com Whisper"""
    try:
        job = jobs_db[job_id]
        job_dir = JOBS_DIR / job_id
        
        print(f"\n🎬 INICIANDO PROCESSAMENTO REAL: {job_id}")
        
        # 1. EXTRAIR ÁUDIO
        print("🎵 Extraindo áudio...")
        job["progress"] = "Extraindo áudio..."
        
        audio_result = audio_extractor.extract_audio(input_path, job_id)
        if not audio_result["success"]:
            raise Exception(f"Erro ao extrair áudio: {audio_result.get('error')}")
        
        audio_path = audio_result["audio_path"]
        print(f"✅ Áudio extraído: {audio_path}")
        
        # 2. TRANSCREVER COM WHISPER
        print("🎤 Transcrevendo com Whisper...")
        job["progress"] = "Transcrevendo áudio (pode demorar)..."
        
        start_time = time.time()
        
        if WHISPER_TYPE == "faster":
            # Faster-whisper
            model = get_whisper_model("base")
            segments, info = model.transcribe(
                audio_path,
                language=None if source_language == "auto" else source_language,  # AQUI
                beam_size=5,
                best_of=5
            )
            
            # Converter para formato padrão
            result_segments = []
            for seg in segments:
                result_segments.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip()
                })
            
            detected_language = info.language
            
        else:
            # OpenAI Whisper
            model = get_whisper_model("base")
            result = model.transcribe(
                audio_path,
                language=None if source_language == "auto" else source_language  # AQUI
            )

            result_segments = []
            for seg in result["segments"]:
                result_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })
            
            detected_language = result.get("language", "unknown")

        job["source_language"] = detected_language
        
        transcription_time = time.time() - start_time
        print(f"✅ Transcrição concluída em {transcription_time:.1f}s")
        print(f"🌐 Idioma detectado: {detected_language}")
        print(f"📝 Total de segmentos: {len(result_segments)}")
        
        # 3. GERAR LEGENDAS
        print("📄 Gerando arquivos de legenda...")
        job["progress"] = "Gerando legendas..."
        
        subtitle_paths = subtitle_generator.generate_subtitles(
            result_segments,
            job_id,
            max_line_width=42,
            max_line_count=2
        )
        
        print(f"✅ Legendas geradas:")
        for format, path in subtitle_paths.items():
            print(f"   - {format}: {path}")
        

        # 4. TRADUZIR (OPCIONAL) - CORRIGIR AQUI
        if detected_language != "pt":  # Usar detected_language ao invés de source_language
            print("🌐 Traduzindo legendas para português...")
            job["progress"] = "Traduzindo para português..."
            
            if translate_subtitles(job_id, "pt"):
                print("✅ Tradução concluída!")
                subtitle_paths["srt_pt"] = f"/storage/legendas-master/temp/subtitles/{job_id}_pt.srt"

        # Atualizar job
        job["status"] = "completed"
        job["completed_at"] = time.time()
        job["duration"] = job["completed_at"] - job["created_at"]
        job["progress"] = "Concluído!"
        job["result"] = {
            "detected_language": detected_language,
            "segments_count": len(result_segments),
            "transcription_time": transcription_time,
            "files": subtitle_paths
        }
        
        print(f"\n✅ JOB {job_id} CONCLUÍDO!")
        print(f"⏱️  Tempo total: {job['duration']:.1f}s")
        
    except Exception as e:
        print(f"\n❌ ERRO no job {job_id}: {str(e)}")
        job["status"] = "failed"
        job["error"] = str(e)
        job["progress"] = f"Erro: {str(e)}"


# Adicione esta função após process_video_real
def translate_subtitles(job_id: str, target_language: str = "pt"):
    """Usa o otimizador para traduzir em 1 chamada"""
    return translation_optimizer.translate_file_optimized(job_id, target_language)
        

@app.get("/api/v1/subtitle/job/{job_id}")
async def get_job_status_real(job_id: str):
    """Status real do job"""
    if job_id not in jobs_db:
        raise HTTPException(404, "Job não encontrado")
    
    job = jobs_db[job_id]
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", ""),
        "created_at": job["created_at"]
    }
    
    if job["status"] == "completed":
        response["download_urls"] = {
            "original": f"/api/v1/download/{job_id}/srt",
            "vtt": f"/api/v1/download/{job_id}/vtt",
            "json": f"/api/v1/download/{job_id}/json"
        }
        response["result"] = job.get("result", {})
        response["duration"] = job.get("duration", 0)
    
    elif job["status"] == "failed":
        response["error"] = job.get("error", "Erro desconhecido")
    
    return response

@app.post("/api/v1/subtitle/translate/{job_id}")
async def translate_job(job_id: str, target_language: str = "pt"):
    """Traduz legendas de um job já processado"""
    if job_id not in jobs_db:
        raise HTTPException(404, "Job não encontrado")
    
    job = jobs_db[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Job ainda não foi concluído")
    
    # Traduzir em thread separada
    import threading
    thread = threading.Thread(
        target=lambda: translate_subtitles(job_id, target_language)
    )
    thread.start()
    
    return {"message": "Tradução iniciada", "job_id": job_id}

@app.get("/api/v1/download/{job_id}/{format}")
async def download_real(job_id: str, format: str):
    """Download real do arquivo"""
    
    # Verificar se é arquivo traduzido
    if "_pt" in job_id:
        # É um arquivo traduzido
        base_job_id = job_id.replace("_pt", "")
        file_path = TEMP_DIR / "subtitles" / f"{base_job_id}_pt.{format}"
    else:
        # Arquivo original
        file_path = TEMP_DIR / "subtitles" / f"{job_id}.{format}"
    
    if not file_path.exists():
        raise HTTPException(404, f"Arquivo {format} não encontrado")
    
    return FileResponse(
        path=file_path,
        filename=f"{job_id}.{format}",
        media_type="text/plain"
    )

# Outros endpoints mock para o frontend funcionar
@app.get("/api/v1/user/usage")
async def usage():
    return {"current_month": {"minutes_used": 10, "minutes_limit": 1000}}

@app.get("/api/v1/user/jobs")
async def user_jobs():
    """Retorna jobs reais com status atualizado"""
    jobs_list = []
    
    for job_id, job in jobs_db.items():
        job_info = {
            "id": job_id,
            "filename": job.get("filename", ""),
            "status": job.get("status", "processing"),
            "created_at": job.get("created_at", time.time()),
            "progress": job.get("progress", ""),
            "error": job.get("error") if job.get("status") == "failed" else None
        }
        
        # IMPORTANTE: Adicionar URLs de download quando concluído
        if job.get("status") == "completed":
            job_info["download_urls"] = {
                "original": f"/api/v1/download/{job_id}/srt",
                "vtt": f"/api/v1/download/{job_id}/vtt",
                "json": f"/api/v1/download/{job_id}/json"
            }
            # Adicionar informações extras do resultado
            if "result" in job:
                job_info["detected_language"] = job["result"].get("detected_language", "unknown")
                job_info["segments_count"] = job["result"].get("segments_count", 0)
                job_info["duration"] = job.get("duration", 0)
        
        jobs_list.append(job_info)
    
    # Ordenar por data (mais recente primeiro)
    jobs_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "jobs": jobs_list,
        "total": len(jobs_list),
        "limit": 20,
        "offset": 0
    }

@app.get("/api/v1/user/stats")
async def stats():
    return {"total_jobs": len(jobs_db), "total_minutes_processed": 50}

@app.get("/api/v1/payment/plans")
async def plans():
    return {"plans": {}, "credit_packages": {}}

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 SERVIDOR REAL - TRANSCRIÇÃO FUNCIONANDO")
    print("="*60)
    print(f"✅ Whisper: {WHISPER_TYPE}")
    print(f"📁 Modelos em: /storage/legendas-master/models/")
    print(f"📁 Jobs em: {JOBS_DIR}")
    print(f"🌐 API: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    print("="*60)
    print("\n⚠️  Primeira transcrição baixa o modelo (~150MB)")
    print("💡 Use arquivo pequeno para testar primeiro!")
    print("\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)