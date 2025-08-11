# backend/services/audio_extractor.py
import ffmpeg
import os
from pathlib import Path
from typing import Dict

class AudioExtractor:
    def __init__(self):
            self.output_dir = Path("/tmp/subtitle-ai/audio")
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_audio(self, video_path: str, output_id: str) -> Dict[str, any]:
        """
        Extrai áudio do vídeo em formato MP3 (menor e mais rápido)
        """
        # MUDAR EXTENSÃO PARA MP3
        audio_path = self.output_dir / f"{output_id}.mp3"
        
        if audio_path.exists():
            print(f"   ⚡ Áudio já existe: {audio_path}")
            return {
                "success": True,
                "audio_path": str(audio_path),
                "cached": True
            }
        
        try:
            print(f"   🔧 Extraindo áudio de: {video_path}")
            print(f"   📁 Salvando em: {audio_path}")
            
            probe = ffmpeg.probe(video_path)
            audio_streams = [s for s in probe['streams'] if s['codec_type'] == 'audio']
            if not audio_streams:
                return {
                    "success": False,
                    "error": "Arquivo não contém áudio"
                }
            
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(
                stream, 
                str(audio_path),
                acodec='libmp3lame',    # Codec MP3
                ar='16000',             # 16kHz (suficiente para fala)
                ac=1,                   # Mono
                b='64k',                # Bitrate 64kbps (bom para fala)
                loglevel='error'
            )
            
            ffmpeg.run(stream, overwrite_output=True)
            
            # Verificar se foi criado
            if audio_path.exists():
                file_size = audio_path.stat().st_size / (1024 * 1024)  # MB
                print(f"   ✅ Áudio extraído: {file_size:.2f} MB")
                
                return {
                    "success": True,
                    "audio_path": str(audio_path),
                    "cached": False,
                    "size_mb": file_size
                }
            else:
                return {
                    "success": False,
                    "error": "Falha ao criar arquivo de áudio"
                }
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"   ❌ Erro FFmpeg: {error_msg}")
            return {
                "success": False,
                "error": f"Erro FFmpeg: {error_msg}"
            }
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_media_duration(self, file_path: str) -> float:
        """
        Retorna duração real do arquivo em segundos
        """
        try:
            probe = ffmpeg.probe(file_path)
            # Procurar stream de vídeo ou áudio
            duration = None
            
            # Tentar pegar do formato geral
            if 'format' in probe and 'duration' in probe['format']:
                duration = float(probe['format']['duration'])
            else:
                # Procurar em streams
                for stream in probe['streams']:
                    if 'duration' in stream:
                        duration = float(stream['duration'])
                        break
            
            if duration:
                print(f"⏱️ Duração detectada: {duration:.1f} segundos ({duration/60:.1f} minutos)")
                return duration
            else:
                print("⚠️ Não foi possível detectar duração")
                return 0
                
        except Exception as e:
            print(f"❌ Erro ao detectar duração: {e}")
            return 0
    
    def convert_to_wav(self, input_path: str, output_path: str) -> bool:
        """
        Converte qualquer áudio para WAV 16kHz
        """
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                acodec='pcm_s16le',
                ar='16000',
                ac=1,
                loglevel='error'
            )
            ffmpeg.run(stream, overwrite_output=True)
            return True
        except:
            return False