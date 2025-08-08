from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import time
import shutil
import hashlib
import asyncio
from pathlib import Path
import os
from config import Config
from models.schemas import SubtitleRequest, SubtitleResponse
from services.vimeo_downloader import VimeoDownloader
from services.audio_extractor import AudioExtractor
from services.transcription import WhisperTranscriber
from services.subtitle_generator import SubtitleGenerator
from services.translator_pro import AISubtitleTranslator, BatchAITranslator
from utils.validators import Validators
from utils.file_manager import FileManager

# Inicializa FastAPI
app = FastAPI(
    title="Video Subtitle API",
    description="API para download de vídeos Vimeo e geração automática de legendas com tradução",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa serviços
downloader = VimeoDownloader()
audio_extractor = AudioExtractor()
subtitle_generator = SubtitleGenerator()

# Inicializa tradutor com IA
translation_provider = os.getenv("TRANSLATION_PROVIDER", "openai")
translator = AISubtitleTranslator(provider=translation_provider)

# Cache de transcritor por modelo
transcribers = {}

def get_transcriber(model_name: str) -> WhisperTranscriber:
    """Obtém ou cria transcritor para o modelo especificado"""
    if model_name not in transcribers:
        transcribers[model_name] = WhisperTranscriber(model_name)
    return transcribers[model_name]

@app.post("/subtitle", response_model=SubtitleResponse)
async def generate_subtitle(request: SubtitleRequest, background_tasks: BackgroundTasks):
    """
    Endpoint principal para gerar legendas com opção de tradução
    """
    start_time = time.time()
    
    # Valida URL
    if not Validators.is_valid_vimeo_url(str(request.vimeo_url)):
        raise HTTPException(status_code=400, detail="URL Vimeo inválida")
    
    try:
        # 1. Download do vídeo
        download_result = downloader.download(str(request.vimeo_url))
        if not download_result["success"]:
            raise HTTPException(status_code=500, detail=f"Erro no download: {download_result['error']}")
        
        video_id = download_result["video_id"]
        video_path = download_result["path"]
        
        # 2. Extração de áudio
        audio_result = audio_extractor.extract_audio(video_path, video_id)
        if not audio_result["success"]:
            raise HTTPException(status_code=500, detail=f"Erro na extração de áudio: {audio_result['error']}")
        
        # 3. Transcrição
        model_name = request.model or Config.WHISPER_MODEL
        transcriber = get_transcriber(model_name)
        
        transcription_result = transcriber.transcribe(
            audio_result["audio_path"],
            request.language
        )
        
        if not transcription_result["success"]:
            raise HTTPException(status_code=500, detail=f"Erro na transcrição: {transcription_result['error']}")
        
        # Detecta idioma se necessário
        detected_language = transcription_result["language"]
        original_segments = transcription_result["segments"]
        
        # 4. Tradução (se solicitado e o idioma não for português)
        translated_segments = None
        was_translated = False
        
        if request.translate_to_pt and detected_language != 'pt':
            try:
                print(f"Traduzindo de {detected_language} para pt-BR...")
                translated_segments = translator.translate_segments(
                    original_segments,
                    source_lang=detected_language,
                    target_lang='pt'
                )
                was_translated = True
            except Exception as e:
                print(f"Erro na tradução: {e}")
                # Continua sem tradução em caso de erro
        
        # 5. Geração de legendas originais
        subtitle_paths = subtitle_generator.generate_subtitles(
            original_segments,
            video_id,
            request.max_line_width,
            request.max_line_count
        )
        
        # 6. Geração de legendas traduzidas (se aplicável)
        translated_paths = {}
        if translated_segments:
            # Gera arquivos com sufixo _pt
            print(f"\n=== DEBUG TRADUÇÃO ===")
            print(f"Primeiro segmento ORIGINAL: {original_segments[0]['text']}")
            print(f"Primeiro segmento TRADUZIDO: {translated_segments[0]['text']}")
            print(f"======================\n")
            
            for seg in translated_segments:
                if 'original_text' in seg and seg['original_text'] != seg['text']:
                    # OK, está traduzido
                    pass
                else:
                    print(f"AVISO: Segmento não traduzido? {seg}")

            translated_paths = subtitle_generator.generate_subtitles(
                translated_segments,
                f"{video_id}_pt",
                request.max_line_width,
                request.max_line_count
            )
        
        # Agenda limpeza de arquivos após 24 horas
        background_tasks.add_task(
            cleanup_files_later, 
            video_id, 
            delay_hours=24
        )
        
        processing_time = time.time() - start_time
        
        # Prepara resposta
        response_data = {
            "success": True,
            "video_id": video_id,
            "srt_path": f"/download/{video_id}/srt",
            "vtt_path": f"/download/{video_id}/vtt",
            "json_path": f"/download/{video_id}/json",
            "processing_time": processing_time,
            "detected_language": detected_language,
            "was_translated": was_translated
        }
        
        # Adiciona caminhos traduzidos se existirem
        if was_translated:
            response_data.update({
                "srt_translated_path": f"/download/{video_id}_pt/srt",
                "vtt_translated_path": f"/download/{video_id}_pt/vtt"
            })
        
        return SubtitleResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{video_id}/{format}")
async def download_subtitle(video_id: str, format: str):
    """
    Download do arquivo de legenda
    """
    if format not in ["srt", "vtt", "json"]:
        raise HTTPException(status_code=400, detail="Formato inválido")
    
    file_path = Config.SUBTITLE_DIR / f"{video_id}.{format}"


    print(f"\n=== DEBUG DOWNLOAD ===")
    print(f"Video ID recebido: {video_id}")
    print(f"Formato: {format}")
    print(f"Procurando arquivo: {file_path}")
    print(f"Arquivo existe? {file_path.exists()}")
    
    # Lista todos os arquivos na pasta para debug
    print("\nArquivos disponíveis:")
    for f in Config.SUBTITLE_DIR.glob("*"):
        print(f"  - {f.name}")
    print("====================\n")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    # Mostra conteúdo do arquivo (primeiras 3 linhas)
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[:5]
        print(f"Conteúdo do arquivo ({file_path.name}):")
        for line in lines:
            print(f"  {line.strip()}")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    # Define nome do arquivo para download
    filename = f"{video_id}"
    if "_pt" in video_id:
        filename = f"{video_id.replace('_pt', '')}_Portuguese"
    
    return FileResponse(
        path=file_path,
        filename=f"{filename}.{format}",
        media_type="text/plain" if format != "json" else "application/json"
    )



@app.post("/translate/{video_id}")
async def translate_existing_subtitle(video_id: str, target_language: str = "pt"):
    """
    Traduz legendas já existentes
    """
    try:
        # Verifica se o arquivo SRT existe
        srt_path = Config.SUBTITLE_DIR / f"{video_id}.srt"
        if not srt_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo SRT não encontrado")
        
        # Lê o arquivo SRT
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        # Traduz
        translated_srt = translator.translate_srt_file(
            srt_content,
            source_lang='en',
            target_lang=target_language
        )
        
        # Salva arquivo traduzido
        translated_path = Config.SUBTITLE_DIR / f"{video_id}_{target_language}.srt"
        with open(translated_path, 'w', encoding='utf-8') as f:
            f.write(translated_srt)
        
        return {
            "success": True,
            "message": "Legenda traduzida com sucesso",
            "download_path": f"/download/{video_id}_{target_language}/srt"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{video_id}")
async def check_status(video_id: str):
    """
    Verifica status de processamento incluindo traduções
    """
    files = {
        "video": (Config.VIDEO_DIR / f"{video_id}.mp4").exists(),
        "audio": (Config.AUDIO_DIR / f"{video_id}.wav").exists(),
        "srt": (Config.SUBTITLE_DIR / f"{video_id}.srt").exists(),
        "srt_pt": (Config.SUBTITLE_DIR / f"{video_id}_pt.srt").exists(),
        "vtt": (Config.SUBTITLE_DIR / f"{video_id}.vtt").exists(),
        "vtt_pt": (Config.SUBTITLE_DIR / f"{video_id}_pt.vtt").exists(),
        "json": (Config.SUBTITLE_DIR / f"{video_id}.json").exists()
    }
    
    return {
        "video_id": video_id,
        "files": files,
        "completed": all([files["srt"], files["vtt"], files["json"]]),
        "has_translation": files["srt_pt"] and files["vtt_pt"]
    }

@app.delete("/cleanup/{video_id}")
async def cleanup_video(video_id: str):
    """
    Remove arquivos de um vídeo específico
    """
    FileManager.cleanup_video_files(video_id)
    # Remove também arquivos traduzidos
    FileManager.cleanup_video_files(f"{video_id}_pt")
    return {"message": "Arquivos removidos com sucesso"}

@app.on_event("startup")
async def startup_event():
    """
    Inicialização da API
    """
    print(f"🚀 API iniciada em http://{Config.API_HOST}:{Config.API_PORT}")
    print(f"📁 Diretório temporário: {Config.TEMP_DIR}")
    print(f"🤖 Modelo Whisper: {Config.WHISPER_MODEL}")
    print(f"💻 Device: {Config.WHISPER_DEVICE}")
    print(f"🌐 Tradução automática: Ativada")
    
    # Limpeza inicial de arquivos antigos
    FileManager.cleanup_old_files(48)

async def cleanup_files_later(video_id: str, delay_hours: int):
    """
    Agenda limpeza de arquivos
    """
    await asyncio.sleep(delay_hours * 3600)
    FileManager.cleanup_video_files(video_id)
    FileManager.cleanup_video_files(f"{video_id}_pt")

@app.get("/")
async def root():
    """
    Endpoint raiz com informações da API
    """
    return {
        "name": "Video Subtitle API",
        "version": "2.0.0",
        "features": {
            "transcription": "Whisper AI",
            "translation": "Google Translate",
            "formats": ["SRT", "VTT", "JSON"]
        },
        "endpoints": {
            "POST /subtitle": "Gera legendas com tradução automática",
            "GET /download/{video_id}/{format}": "Download da legenda",
            "POST /translate/{video_id}": "Traduz legenda existente",
            "GET /status/{video_id}": "Verifica status do processamento",
            "DELETE /cleanup/{video_id}": "Remove arquivos do vídeo"
        }
    }


@app.post("/upload-video")
async def upload_video_manual(
    file: UploadFile = File(...),
    translate_to_pt: bool = True,  # Mantém por compatibilidade mas não usa
    language: str = "auto",
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload manual de vídeo para processar legendas"""
    start_time = time.time()
    
    try:
        # Validações
        if not file.filename.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
            raise HTTPException(
                status_code=400, 
                detail="Formato não suportado. Use: MP4, MOV, AVI, MKV ou WEBM"
            )
        
        # Verifica tamanho (limite de 1GB)
        file.file.seek(0, 2)  # Move para o final
        file_size = file.file.tell()  # Pega posição (tamanho)
        file.file.seek(0)  # Volta ao início
        
        if file_size > 1024 * 1024 * 1024:  # 1GB
            raise HTTPException(
                status_code=400,
                detail="Arquivo muito grande. Máximo: 1GB"
            )
        
        # Gera ID único
        video_id = hashlib.md5(f"{file.filename}{time.time()}".encode()).hexdigest()[:12]
        video_path = Config.VIDEO_DIR / f"{video_id}.mp4"
        
        # Salva arquivo
        print(f"Salvando arquivo: {file.filename} -> {video_path}")
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Extração de áudio (converte para MP3/WAV)
        print("Extraindo áudio...")
        audio_result = audio_extractor.extract_audio(str(video_path), video_id)
        if not audio_result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro na extração de áudio: {audio_result['error']}"
            )
        
        print("Iniciando transcrição...")
        model_name = Config.WHISPER_MODEL
        transcriber = get_transcriber(model_name)
        
        transcription_result = transcriber.transcribe(
            audio_result["audio_path"],
            language
        )
        
        if not transcription_result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro na transcrição: {transcription_result['error']}"
            )
        
        # Detecta idioma
        detected_language = transcription_result["language"]
        original_segments = transcription_result["segments"]
        
    
        
        # 5. Geração de legendas
        subtitle_paths = subtitle_generator.generate_subtitles(
            original_segments,
            video_id,
            max_line_width=42,
            max_line_count=2
        )
        
    
        
        # Agenda limpeza
        background_tasks.add_task(
            cleanup_files_later, 
            video_id, 
            delay_hours=24
        )
        
        processing_time = time.time() - start_time
        
        # Resposta
        return {
            "success": True,
            "video_id": video_id,
            "filename": file.filename,
            "processing_time": round(processing_time, 2),
            "detected_language": detected_language,
            "was_translated": False,  # Sempre false agora
            "downloads": {
                "srt_original": f"/download/{video_id}/srt",
                "vtt_original": f"/download/{video_id}/vtt",
                "json": f"/download/{video_id}/json",
                # Indica que tradução está disponível sob demanda
                "srt_portuguese": f"/download-translated/{video_id}/srt" if detected_language != 'pt' else None,
                "vtt_portuguese": f"/download-translated/{video_id}/vtt" if detected_language != 'pt' else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-upload")
async def test_upload_page():
    """Retorna página de teste de upload"""
    return HTMLResponse(content=open("interface.html", "r", encoding="utf-8").read())


@app.get("/download-translated/{video_id}/{format}")
async def download_translated_on_demand(video_id: str, format: str):
    """
    Tradução inteligente sob demanda - traduz apenas quando solicitado
    """
    if format not in ["srt", "vtt"]:
        raise HTTPException(400, "Apenas SRT e VTT suportados")
    
    # Verifica se já existe tradução em cache
    cached_path = Config.SUBTITLE_DIR / f"{video_id}_pt.{format}"
    if cached_path.exists():
        print(f"Usando tradução em cache: {cached_path}")
        return FileResponse(
            path=cached_path,
            filename=f"{video_id}_Portuguese.{format}",
            media_type="text/plain"
        )
    
    # Se não existe, traduz agora
    original_path = Config.SUBTITLE_DIR / f"{video_id}.{format}"
    if not original_path.exists():
        raise HTTPException(404, "Arquivo original não encontrado")
    
    print(f"Traduzindo sob demanda: {video_id}")
    
    # Lê o arquivo original
    with open(original_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Usa o tradutor já configurado
    try:
        # Para SRT, traduz diretamente
        if format == "srt":
            translated_content = translator.translate_srt_file(
                content,
                source_lang='en',
                target_lang='pt'
            )
        else:  # VTT
            # Converte VTT para formato similar ao SRT para tradução
            translated_content = translator.translate_vtt_file(
                content,
                source_lang='en', 
                target_lang='pt'
            )
        
        # Salva em cache para próximas vezes
        with open(cached_path, 'w', encoding='utf-8') as f:
            f.write(translated_content)
        
        print(f"Tradução concluída e salva em cache: {cached_path}")
        
        return FileResponse(
            path=cached_path,
            filename=f"{video_id}_Portuguese.{format}",
            media_type="text/plain"
        )
        
    except Exception as e:
        print(f"Erro na tradução: {e}")
        raise HTTPException(500, f"Erro na tradução: {str(e)}")
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )


