import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    # Whisper
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
    
    # File Management
    MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", 1000))
    ALLOWED_VIDEO_EXTENSIONS = os.getenv("ALLOWED_VIDEO_EXTENSIONS", ".mp4,.mov,.avi,.mkv").split(",")
    
    # Paths
    BASE_DIR = Path(__file__).parent
    TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp"))
    VIDEO_DIR = TEMP_DIR / "videos"
    AUDIO_DIR = TEMP_DIR / "audio"
    SUBTITLE_DIR = TEMP_DIR / "subtitles"
    
    @classmethod
    def create_directories(cls):
        """Cria diretórios necessários"""
        for directory in [cls.VIDEO_DIR, cls.AUDIO_DIR, cls.SUBTITLE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

Config.create_directories()