# services/video_downloader_universal.py
import os
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any
import requests
from config import Config
import sys


class UniversalVideoDownloader:
    def __init__(self):
        self.output_dir = Config.VIDEO_DIR
        
    def download(self, video_url: str) -> Dict[str, Any]:
        """Download universal que tenta vários métodos"""
        video_id = hashlib.md5(video_url.encode()).hexdigest()[:12]
        output_path = self.output_dir / f"{video_id}.mp4"
        
        # Se já existe
        if output_path.exists():
            return {
                "success": True,
                "video_id": video_id,
                "path": str(output_path),
                "cached": True
            }
        
        # Tenta diferentes métodos
        print(f"Tentando baixar: {video_url}")
        
        # Método 1: Streamlink
        if self._try_streamlink(video_url, output_path):
            return {
                "success": True,
                "video_id": video_id,
                "path": str(output_path),
                "cached": False
            }
            
        # Método 2: youtube-dl (versão antiga, mais compatível)
        if self._try_youtube_dl(video_url, output_path):
            return {
                "success": True,
                "video_id": video_id,
                "path": str(output_path),
                "cached": False
            }
            
        # Método 3: Download direto se for URL de vídeo
        if self._try_direct_download(video_url, output_path):
            return {
                "success": True,
                "video_id": video_id,
                "path": str(output_path),
                "cached": False
            }
            
        return {
            "success": False,
            "error": "Não foi possível baixar. Tente fazer upload manual do arquivo.",
            "video_id": video_id
        }
    
    def _try_streamlink(self, url: str, output_path: Path) -> bool:
        """Tenta com Streamlink"""
        try:
            print("Tentando com Streamlink...")
            cmd = [
                "streamlink",
                url,
                "best",
                "-o", str(output_path),
                "--force"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if output_path.exists() and output_path.stat().st_size > 1000:
                print("✓ Sucesso com Streamlink")
                return True
                
        except Exception as e:
            print(f"Streamlink falhou: {e}")
            
        return False
    
    def _try_youtube_dl(self, url: str, output_path: Path) -> bool:
        """Tenta com youtube-dl clássico"""
        try:
            print("Tentando com youtube-dl...")
            # Instala youtube-dl se não tiver
            subprocess.run([sys.executable, "-m", "pip", "install", "youtube-dl"], 
                         capture_output=True)
            
            cmd = [
                "youtube-dl",
                "-f", "best",
                "-o", str(output_path),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if output_path.exists() and output_path.stat().st_size > 1000:
                print("✓ Sucesso com youtube-dl")
                return True
                
        except Exception as e:
            print(f"youtube-dl falhou: {e}")
            
        return False
    
    def _try_direct_download(self, url: str, output_path: Path) -> bool:
        """Tenta download direto se for URL .mp4"""
        try:
            if '.mp4' in url or 'video' in url:
                print("Tentando download direto...")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, stream=True, timeout=30)
                
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    if output_path.exists() and output_path.stat().st_size > 1000:
                        print("✓ Sucesso com download direto")
                        return True
                        
        except Exception as e:
            print(f"Download direto falhou: {e}")
            
        return False