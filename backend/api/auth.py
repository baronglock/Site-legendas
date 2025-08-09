# backend/api/auth.py
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import secrets

from config import Config
from models.schemas import UserRegister, UserLogin, TokenResponse
from models.database import UserModel, UsageModel, IPBlockModel
from services.auth_service import AuthService
from utils.rate_limiter import RateLimiter

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# Inicializa serviços
auth_service = AuthService()
rate_limiter = RateLimiter()
user_model = UserModel()
usage_model = UsageModel()
ip_block_model = IPBlockModel()

def get_client_ip(request: Request) -> str:
    """Obtém IP real do cliente"""
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valida token e retorna usuário"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user = user_model.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return user

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, request: Request):
    """
    Registra novo usuário
    """
    ip = get_client_ip(request)
    
    # Verifica rate limit
    allowed, info = rate_limiter.check_rate_limit(ip, 'api_calls', 'free')
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Limite excedido. Tente em {info['reset_in']} segundos")
    
    # Verifica IP bloqueado
    if ip_block_model.is_blocked(ip):
        raise HTTPException(status_code=403, detail="IP temporariamente bloqueado")
    
    # Verifica quantas contas esse IP criou
    account_count = ip_block_model.count_user_creations(ip, hours=24)
    if account_count >= Config.FREE_DAILY_UPLOADS:
        ip_block_model.block_ip(ip, "Muitas contas criadas", hours=24)
        raise HTTPException(status_code=403, detail="Limite de contas por IP excedido")
    
    # Verifica se email já existe
    existing_user = user_model.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    try:
        # Cria usuário
        user = user_model.create(user_data.email, ip)
        
        # Inicializa uso mensal
        usage = usage_model.initialize_month(user['id'])
        
        # Cria token
        access_token = create_access_token(data={"sub": user['id']})
        
        return TokenResponse(
            access_token=access_token,
            user_id=user['id'],
            plan="free",
            minutes_available=usage['minutes_limit']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
    """
    Login de usuário existente
    """
    ip = get_client_ip(request)
    
    # Verifica rate limit
    allowed, info = rate_limiter.check_rate_limit(ip, 'api_calls', 'free')
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Limite excedido. Tente em {info['reset_in']} segundos")
    
    # Busca usuário
    user = user_model.get_by_email(user_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Atualiza último IP
    user_model.update_last_ip(user['id'], ip)
    
    # Pega uso atual
    usage = usage_model.get_current_month_usage(user['id'])
    
    # Cria token
    access_token = create_access_token(data={"sub": user['id']})
    
    return TokenResponse(
        access_token=access_token,
        user_id=user['id'],
        plan=user.get('current_plan', 'free'),
        minutes_available=usage['minutes_limit'] - usage['minutes_used']
    )

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Retorna informações do usuário atual
    """
    # Pega uso atual
    usage = usage_model.get_current_month_usage(current_user['id'])
    
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "plan": current_user.get('current_plan', 'free'),
        "created_at": current_user['created_at'],
        "usage": {
            "minutes_used": usage['minutes_used'],
            "minutes_limit": usage['minutes_limit'],
            "minutes_available": usage['minutes_limit'] - usage['minutes_used'],
            "translation_minutes_used": usage['translation_minutes_used']
        }
    }

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Atualiza token de acesso
    """
    access_token = create_access_token(data={"sub": current_user['id']})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout (invalida token no cliente)
    """
    # Em uma implementação mais robusta, você poderia adicionar o token a uma blacklist
    # Por enquanto, o logout é feito apenas no cliente
    return {"message": "Logout realizado com sucesso"}