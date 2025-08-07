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
    translate_to_pt: bool = True,
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
        
        # 3. Transcrição
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
        
        # 4. Tradução (se necessário)
        translated_segments = None
        was_translated = False
        
        if translate_to_pt and detected_language != 'pt':
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
        
        # 5. Geração de legendas
        subtitle_paths = subtitle_generator.generate_subtitles(
            original_segments,
            video_id,
            max_line_width=42,
            max_line_count=2
        )
        
        # 6. Legendas traduzidas
        translated_paths = {}
        if translated_segments:
            translated_paths = subtitle_generator.generate_subtitles(
                translated_segments,
                f"{video_id}_pt",
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
            "was_translated": was_translated,
            "downloads": {
                "srt_original": f"/download/{video_id}/srt",
                "vtt_original": f"/download/{video_id}/vtt",
                "json": f"/download/{video_id}/json",
                "srt_portuguese": f"/download/{video_id}_pt/srt" if was_translated else None,
                "vtt_portuguese": f"/download/{video_id}_pt/vtt" if was_translated else None
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
async def download_translated_realtime(video_id: str, format: str):

    """
    Tradução inteligente que junta fragmentos pequenos
    """
    
    # Define a função auxiliar DENTRO do endpoint
    def calculate_duration(start_time: str, end_time: str) -> float:
        """Calcula duração em segundos"""
        def time_to_seconds(time_str):
            time_str = time_str.replace(',', '.')
            h, m, s = time_str.split(':')
            return float(h) * 3600 + float(m) * 60 + float(s)
        
        return time_to_seconds(end_time) - time_to_seconds(start_time)
    
    if format != "srt":
        raise HTTPException(400, "Apenas SRT suportado")
    
    original_path = Config.SUBTITLE_DIR / f"{video_id}.{format}"
    
    with open(original_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Primeiro, processa o SRT para juntar fragmentos
    blocks = content.strip().split('\n\n')
    processed_blocks = []
    
    i = 0
    while i < len(blocks):
        lines = blocks[i].strip().split('\n')
        if len(lines) >= 3:
            current_number = lines[0]
            current_timing = lines[1]
            current_text = ' '.join(lines[2:])
            
            # Pega o tempo inicial
            start_time = current_timing.split(' --> ')[0]
            end_time = current_timing.split(' --> ')[1]
            
            # Verifica próximos blocos para juntar fragmentos
            combined_text = current_text
            j = i + 1
            
            while j < len(blocks):
                next_lines = blocks[j].strip().split('\n')
                if len(next_lines) >= 3:
                    next_text = ' '.join(next_lines[2:])
                    next_end_time = next_lines[1].split(' --> ')[1]
                    
                    # Condições para juntar:
                    should_merge = False
                    
                    # Verifica se deve juntar
                    if len(next_text.split()) <= 3:  # 3 palavras ou menos
                        should_merge = True
                    elif next_text[0].islower():  # Começa com minúscula
                        should_merge = True
                    elif not current_text.strip().endswith(('.', '!', '?', ':')):  # Não tem pontuação final
                        should_merge = True
                    
                    # Verifica duração total (SEM self.)
                    if should_merge:
                        total_duration = calculate_duration(start_time, next_end_time)  # ← CORRIGIDO
                        if total_duration > 4.0:  # Máximo 4 segundos
                            should_merge = False
                    
                    if should_merge:
                        combined_text += ' ' + next_text
                        end_time = next_end_time
                        j += 1
                    else:
                        break
                else:
                    break
            
            # Cria bloco combinado
            new_timing = f"{start_time} --> {end_time}"
            processed_block = f"{current_number}\n{new_timing}\n{combined_text}"
            processed_blocks.append(processed_block)
            
            i = j  # Pula os blocos que foram combinados
        else:
            processed_blocks.append(blocks[i])
            i += 1
    
    # Reconstrói o SRT processado
    processed_content = '\n\n'.join(processed_blocks)
    
    # Agora traduz com GPT
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""Traduza este arquivo SRT do inglês para português brasileiro.

REGRAS IMPORTANTES:
1. Mantenha EXATAMENTE os mesmos números e timings
2. Traduza de forma natural e fluente
3. O texto deve caber confortavelmente no tempo disponível
4. Mantenha frases completas sempre que possível
5. Use linguagem coloquial para legendas

SRT para traduzir:
{processed_content}

Retorne APENAS o SRT traduzido, mantendo o formato exato."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Você é um tradutor especialista em legendagem."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=4000
    )
    
    translated_srt = response.choices[0].message.content
    translated_srt = translated_srt.replace("```srt", "").replace("```", "").strip()
    
    return Response(
        content=translated_srt,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={video_id}_Portuguese_Smart.{format}"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )


