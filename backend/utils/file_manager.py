import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from config import Config

class FileManager:
    @staticmethod
    def cleanup_old_files(hours: int = 24):
        """Remove arquivos mais antigos que X horas"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for directory in [Config.VIDEO_DIR, Config.AUDIO_DIR, Config.SUBTITLE_DIR]:
            for file_path in directory.glob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
    
    @staticmethod
    def get_file_size_mb(file_path: Path) -> float:
        """Retorna tamanho do arquivo em MB"""
        return file_path.stat().st_size / (1024 * 1024)
    
    @staticmethod
    def cleanup_video_files(video_id: str):
        """Remove todos os arquivos de um vídeo específico"""
        patterns = [
            Config.VIDEO_DIR / f"{video_id}.*",
            Config.AUDIO_DIR / f"{video_id}.*",
            Config.SUBTITLE_DIR / f"{video_id}.*"
        ]
        
        for pattern in patterns:
            for file_path in pattern.parent.glob(pattern.name):
                if file_path.exists():
                    file_path.unlink()