# backend/api/__init__.py
from fastapi import APIRouter
from .auth import router as auth_router
from .subtitle import router as subtitle_router
from .payment import router as payment_router
from .user import router as user_router

# Cria router principal da API
api_router = APIRouter(prefix="/api/v1")

# Registra todos os routers
api_router.include_router(auth_router)
api_router.include_router(subtitle_router)
api_router.include_router(payment_router)
api_router.include_router(user_router)

__all__ = ['api_router']