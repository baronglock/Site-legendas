# backend/services/auth_service.py
from typing import Optional, Dict
import hashlib
from datetime import datetime, timedelta
from supabase import create_client, Client
import os
import secrets
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from config import Config
from models.database import UserModel, IPBlockModel, UsageModel

class AuthService:
    def __init__(self):
        self.user_model = UserModel()
        self.ip_block_model = IPBlockModel()
        self.usage_model = UsageModel()
    
    def create_user(self, email: str, ip: str) -> Dict:
        """
        Cria novo usuário com verificações anti-abuse
        """
        # Verifica IP bloqueado
        if self.ip_block_model.is_blocked(ip):
            raise HTTPException(400, "IP temporariamente bloqueado")
        
        # Verifica quantas contas esse IP criou hoje
        if self.ip_block_model.count_user_creations(ip) >= Config.FREE_DAILY_UPLOADS:
            self.ip_block_model.block_ip(ip, "Muitas contas criadas", hours=24)
            raise HTTPException(400, "Limite de contas por IP excedido")
        
        try:
            # Cria usuário
            user = self.user_model.create(email, ip)
            
            if not user:
                raise HTTPException(500, "Erro ao criar usuário")
            
            # Inicializa uso mensal
            self.usage_model.initialize_month(user['id'])
            
            return {
                'success': True,
                'user_id': user['id'],
                'email': user['email']
            }
            
        except Exception as e:
            if 'duplicate key' in str(e) or 'already exists' in str(e):
                raise HTTPException(400, "Email já cadastrado")
            raise HTTPException(500, str(e))
    
    def verify_user_credentials(self, email: str) -> Optional[Dict]:
        """
        Verifica credenciais do usuário (simplificado - sem senha por enquanto)
        """
        user = self.user_model.get_by_email(email)
        if not user:
            return None
        
        return user
    
    def get_client_ip(self, request: Request) -> str:
        """
        Obtém IP real do cliente considerando proxies
        """
        # Verifica headers de proxy
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Cloudflare
        cf_ip = request.headers.get('CF-Connecting-IP')
        if cf_ip:
            return cf_ip
        
        # IP direto
        return request.client.host if request.client else '0.0.0.0'
    
    def check_user_limits(self, user_id: str, required_minutes: float) -> Dict:
        """
        Verifica se usuário tem créditos suficientes
        """
        can_use, info = self.usage_model.can_use(user_id, required_minutes)
        
        return {
            'allowed': can_use,
            'available_minutes': info['available'],
            'requested_minutes': info['requested'],
            'used_minutes': info['used'],
            'limit_minutes': info['limit']
        }
    
    def consume_user_credits(self, user_id: str, minutes_used: float, 
                           translation_minutes: float = 0) -> bool:
        """
        Consome créditos do usuário
        """
        try:
            self.usage_model.consume_minutes(user_id, minutes_used, translation_minutes)
            return True
        except Exception as e:
            print(f"Erro ao consumir créditos: {e}")
            return False
    
    def get_user_plan_details(self, user_id: str) -> Dict:
        """
        Retorna detalhes do plano do usuário
        """
        user = self.user_model.get_by_id(user_id)
        if not user:
            return None
        
        plan = user.get('current_plan', 'free')
        
        # Mapeia detalhes do plano
        plan_details = {
            'free': {
                'name': 'Gratuito',
                'whisper_model': Config.WHISPER_MODEL_FREE,
                'translation_model': Config.TRANSLATION_MODEL_FREE,
                'max_file_size_mb': Config.MAX_FILE_SIZE_MB_FREE,
                'priority': 0,
                'queue': 'free'
            },
            'starter': {
                'name': 'Iniciante',
                'whisper_model': Config.WHISPER_MODEL_FREE,
                'translation_model': Config.TRANSLATION_MODEL_PAID,
                'max_file_size_mb': 200,
                'priority': 5,
                'queue': 'paid'
            },
            'pro': {
                'name': 'Pro',
                'whisper_model': Config.WHISPER_MODEL_PAID,
                'translation_model': Config.TRANSLATION_MODEL_PAID,
                'max_file_size_mb': 500,
                'priority': 10,
                'queue': 'paid'
            },
            'premium': {
                'name': 'Premium',
                'whisper_model': Config.WHISPER_MODEL_PAID,
                'translation_model': Config.TRANSLATION_MODEL_PAID,
                'max_file_size_mb': Config.MAX_FILE_SIZE_MB_PAID,
                'priority': 20,
                'queue': 'priority'
            },
            'enterprise': {
                'name': 'Enterprise',
                'whisper_model': Config.WHISPER_MODEL_PAID,
                'translation_model': Config.TRANSLATION_MODEL_PAID,
                'max_file_size_mb': 2000,
                'priority': 100,
                'queue': 'priority'
            }
        }
        
        return plan_details.get(plan, plan_details['free'])
    
    def check_referral_bonus(self, email: str) -> Optional[int]:
        """
        Verifica se email foi indicado e retorna bônus
        """
        from models.database import Database
        db = Database.get_client()
        
        # Busca indicação
        result = db.table('referrals').select('*').eq(
            'referred_email', email
        ).is_('claimed_at', 'null').execute()
        
        if result.data:
            referral = result.data[0]
            
            # Marca como resgatado
            db.table('referrals').update({
                'claimed_at': datetime.utcnow().isoformat()
            }).eq('id', referral['id']).execute()
            
            # Adiciona bônus ao indicador
            referrer_id = referral['referrer_user_id']
            bonus_minutes = referral['bonus_minutes']
            
            # Adiciona minutos ao usuário que indicou
            current_month = datetime.now().strftime('%Y-%m')
            usage = db.table('usage_credits').select('*').eq(
                'user_id', referrer_id
            ).eq('month_year', current_month).execute()
            
            if usage.data:
                current_limit = usage.data[0]['minutes_limit']
                db.table('usage_credits').update({
                    'minutes_limit': current_limit + bonus_minutes
                }).eq('id', usage.data[0]['id']).execute()
            
            return bonus_minutes
        
        return None