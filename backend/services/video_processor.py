# backend/services/video_processor.py
import os
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Optional, BinaryIO
import yt_dlp
import ffmpeg
import requests
from urllib.parse import urlparse
from config import Config
from utils.r2_storage import R2Storage

class VideoProcessor:
    def __init__(self):
        self.r2 = R2Storage()
        self.temp_dir = tempfile.gettempdir()
        
    def process_upload(self, file: BinaryIO, filename: str, user_id: str) -> Dict:
        """
        Processa upload direto de arquivo
        """
        # Gera ID único para o job
        job_id = self._generate_job_id(f"{user_id}{filename}")
        
        # Salva temporariamente
        temp_path = Path(self.temp_dir) / f"{job_id}_{filename}"
        
        try:
            # Salva arquivo temporário
            with open(temp_path, 'wb') as f:
                while chunk := file.read(8192):
                    f.write(chunk)
            
            # Extrai áudio
            audio_path = self._extract_audio(temp_path, job_id)
            
            # Upload para R2
            r2_result = self.r2.upload_file(
                str(audio_path),
                user_id,
                'audio'
            )
            
            # Limpa arquivos temporários
            temp_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
            
            if r2_result['success']:
                return {
                    'success': True,
                    'job_id': job_id,
                    'audio_key': r2_result['key'],
                    'audio_url': r2_result['url'],
                    'duration': self._get_duration(str(temp_path))
                }
            else:
                return {
                    'success': False,
                    'error': r2_result.get('error', 'Upload para R2 falhou')
                }
                
        except Exception as e:
            # Limpa em caso de erro
            temp_path.unlink(missing_ok=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_url(self, url: str, user_id: str) -> Dict:
        """
        Processa download de URL (YouTube, Vimeo, etc)
        """
        job_id = self._generate_job_id(f"{user_id}{url}")
        
        # Detecta plataforma
        platform = self._detect_platform(url)
        
        try:
            # Configuração do yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(Path(self.temp_dir) / f'{job_id}.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'extract_audio': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            # Download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Pega o arquivo de áudio
                audio_path = Path(self.temp_dir) / f"{job_id}.mp3"
                
                if not audio_path.exists():
                    # Tenta com .m4a ou outros formatos
                    for ext in ['.m4a', '.webm', '.opus']:
                        test_path = Path(self.temp_dir) / f"{job_id}{ext}"
                        if test_path.exists():
                            audio_path = test_path
                            break
                
                if audio_path.exists():
                    # Upload para R2
                    r2_result = self.r2.upload_file(
                        str(audio_path),
                        user_id,
                        'audio'
                    )
                    
                    # Limpa arquivo temporário
                    audio_path.unlink(missing_ok=True)
                    
                    if r2_result['success']:
                        return {
                            'success': True,
                            'job_id': job_id,
                            'audio_key': r2_result['key'],
                            'audio_url': r2_result['url'],
                            'duration': info.get('duration', 0),
                            'title': info.get('title', 'Unknown'),
                            'platform': platform
                        }
                
                return {
                    'success': False,
                    'error': 'Não foi possível extrair áudio'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro no download: {str(e)}'
            }
    
    def _extract_audio(self, video_path: Path, job_id: str) -> Path:
        """
        Extrai áudio de vídeo para formato WAV 16kHz (ideal para Whisper)
        """
        audio_path = Path(self.temp_dir) / f"{job_id}.wav"
        
        try:
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(audio_path),
                acodec='pcm_s16le',  # WAV 16-bit
                ar='16000',          # 16kHz para Whisper
                ac=1,                # Mono
                loglevel='error'
            )
            ffmpeg.run(stream, overwrite_output=True)
            
            return audio_path
            
        except Exception as e:
            raise Exception(f"Erro na extração de áudio: {e}")
    
    def _get_duration(self, file_path: str) -> float:
        """
        Obtém duração do arquivo em segundos
        """
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except:
            return 0.0
    
    def _generate_job_id(self, seed: str) -> str:
        """
        Gera ID único para o job
        """
        return hashlib.md5(f"{seed}{os.urandom(8).hex()}".encode()).hexdigest()[:12]
    
    def _detect_platform(self, url: str) -> str:
        """
        Detecta plataforma do vídeo
        """
        domain = urlparse(url).netloc.lower()
        
        platforms = {
            'youtube.com': 'youtube',
            'youtu.be': 'youtube',
            'vimeo.com': 'vimeo',
            'dailymotion.com': 'dailymotion',
            'facebook.com': 'facebook',
            'instagram.com': 'instagram',
            'twitter.com': 'twitter',
            'x.com': 'twitter',
            'tiktok.com': 'tiktok'
        }
        
        for key, platform in platforms.items():
            if key in domain:
                return platform
        
        return 'unknown'