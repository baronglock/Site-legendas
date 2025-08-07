import ffmpeg
import os
from pathlib import Path
from config import Config
from typing import Dict

class AudioExtractor:
    def __init__(self):
        self.output_dir = Config.AUDIO_DIR
    
    def extract_audio(self, video_path: str, video_id: str) -> Dict[str, any]:
        """
        Extrai áudio do vídeo em formato WAV 16kHz (ideal para Whisper)
        """
        audio_path = self.output_dir / f"{video_id}.wav"
        
        # Se já existe, retorna
        if audio_path.exists():
            return {
                "success": True,
                "audio_path": str(audio_path),
                "cached": True
            }
        
        try:
            # Extrai áudio com configurações otimizadas para Whisper
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(
                stream, 
                str(audio_path),
                acodec='pcm_s16le',  # WAV 16-bit
                ar='16000',          # 16kHz (recomendado para Whisper)
                ac=1,                # Mono
                loglevel='error'
            )
            ffmpeg.run(stream, overwrite_output=True)
            
            return {
                "success": True,
                "audio_path": str(audio_path),
                "cached": False
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }