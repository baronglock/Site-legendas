# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Environment
    ENV = os.getenv("ENVIRONMENT", "development")
    DEBUG = ENV == "development"
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    # Whisper Models - Baseado no plano
    WHISPER_MODEL_FREE = os.getenv("WHISPER_MODEL_FREE", "base")
    WHISPER_MODEL_PAID = os.getenv("WHISPER_MODEL_PAID", "large-v3")
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
    
    # Translation Models - USANDO GPT-5 COMO VOCÊ PEDIU!
    TRANSLATION_MODEL_FREE = os.getenv("TRANSLATION_MODEL_FREE", "gpt-5-nano")
    TRANSLATION_MODEL_PAID = os.getenv("TRANSLATION_MODEL_PAID", "gpt-5-mini")
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
    # Cloudflare R2
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
    R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
    R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
    R2_ENDPOINT = os.getenv("R2_ENDPOINT")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Redis/Queue (quando configurar)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Stripe (quando configurar)
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # RunPod (quando adicionar créditos)
    RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
    
    # Limites e Planos
    FREE_MINUTES_LIMIT = int(os.getenv("FREE_MINUTES_LIMIT", 20))
    FREE_DAILY_UPLOADS = int(os.getenv("FREE_DAILY_UPLOADS", 3))
    MAX_FILE_SIZE_MB_FREE = int(os.getenv("MAX_FILE_SIZE_MB_FREE", 50))
    MAX_FILE_SIZE_MB_PAID = int(os.getenv("MAX_FILE_SIZE_MB_PAID", 1000))
    
    # Segurança
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-here")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))
    
    # File Management
    ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    ALLOWED_AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".aac"]
    
    # Paths (não usaremos mais local, mas mantém para compatibilidade)
    BASE_DIR = Path(__file__).parent
    
    @classmethod
    def validate(cls):
        """Valida configurações essenciais"""
        required = [
            "SUPABASE_URL", "SUPABASE_ANON_KEY", 
            "R2_ACCOUNT_ID", "R2_ACCESS_KEY", "R2_SECRET_KEY",
            "OPENAI_API_KEY"
        ]
        
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            raise ValueError(f"Configurações faltando: {', '.join(missing)}")
        
        return True

# Valida ao importar
if Config.ENV == "production":
    Config.validate()