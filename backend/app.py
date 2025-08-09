# backend/app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from pathlib import Path
import os
from config import Config
from api import api_router
from models.database import Database

# Inicializa FastAPI
app = FastAPI(
    title="Video Subtitle API",
    description="API para transcrição e tradução automática de vídeos com IA",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui todos os routers da API
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """
    Inicialização da API
    """
    print(f"🚀 API iniciada em http://{Config.API_HOST}:{Config.API_PORT}")
    print(f"📊 Ambiente: {Config.ENV}")
    print(f"🤖 Modelos Whisper: {Config.WHISPER_MODEL_FREE} (free) / {Config.WHISPER_MODEL_PAID} (paid)")
    print(f"🌐 Modelos de Tradução: {Config.TRANSLATION_MODEL_FREE} (free) / {Config.TRANSLATION_MODEL_PAID} (paid)")
    print(f"☁️ Storage: Cloudflare R2")
    print(f"💾 Banco de dados: Supabase")
    
    # Testa conexão com banco de dados
    if Database.test_connection():
        print("✅ Conexão com Supabase OK!")
    else:
        print("❌ Erro na conexão com Supabase - verifique as credenciais")
    
    # Valida configurações em produção
    if Config.ENV == "production":
        try:
            Config.validate()
            print("✅ Configurações validadas")
        except ValueError as e:
            print(f"❌ Erro nas configurações: {e}")
            raise

@app.get("/")
async def root():
    """
    Endpoint raiz com informações da API
    """
    return {
        "name": "Video Subtitle API",
        "version": "3.0.0",
        "status": "online",
        "features": {
            "transcription": {
                "models": {
                    "free": Config.WHISPER_MODEL_FREE,
                    "paid": Config.WHISPER_MODEL_PAID
                }
            },
            "translation": {
                "models": {
                    "free": Config.TRANSLATION_MODEL_FREE,
                    "paid": Config.TRANSLATION_MODEL_PAID
                }
            },
            "storage": "Cloudflare R2",
            "database": "Supabase",
            "formats": ["SRT", "VTT", "JSON"]
        },
        "plans": {
            "free": "20 minutos/mês",
            "starter": "$9.99 - 2 horas/mês",
            "pro": "$19.99 - 5 horas/mês",
            "premium": "$49.99 - 15 horas/mês"
        },
        "api_docs": "/docs",
        "api_redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    checks = {
        "api": "ok",
        "database": "unknown",
        "storage": "unknown"
    }
    
    # Verifica banco de dados
    try:
        if Database.test_connection():
            checks["database"] = "ok"
        else:
            checks["database"] = "error"
    except:
        checks["database"] = "error"
    
    # Verifica R2 (implementar teste de conexão)
    try:
        from utils.r2_storage import R2Storage
        r2 = R2Storage()
        # Implementar teste simples
        checks["storage"] = "ok"
    except:
        checks["storage"] = "error"
    
    # Status geral
    all_ok = all(status == "ok" for status in checks.values())
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": int(time.time()),
        "checks": checks
    }

# Handler de erros global
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": int(time.time())
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    # Log do erro (implementar logging apropriado)
    print(f"Erro não tratado: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erro interno do servidor",
            "status_code": 500,
            "timestamp": int(time.time())
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=Config.ENV == "development"
    )