# backend/models/database.py
from supabase import create_client, Client
from typing import Optional
import os
from datetime import datetime
from config import Config

class Database:
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Singleton para cliente Supabase"""
        if cls._instance is None:
            cls._instance = create_client(
                Config.SUPABASE_URL,
                Config.SUPABASE_SERVICE_KEY  # Usa service key para operações backend
            )
        return cls._instance
    
    @classmethod
    def test_connection(cls) -> bool:
        """Testa conexão com Supabase"""
        try:
            client = cls.get_client()
            # Tenta fazer uma query simples
            result = client.table('users').select('id').limit(1).execute()
            print("✅ Conexão com Supabase OK!")
            return True
        except Exception as e:
            print(f"❌ Erro na conexão Supabase: {e}")
            return False

class UserModel:
    def __init__(self):
        self.db = Database.get_client()
        
    def create(self, email: str, ip: str) -> dict:
        """Cria novo usuário"""
        data = {
            'email': email,
            'last_ip': ip,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.db.table('users').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_by_email(self, email: str) -> Optional[dict]:
        """Busca usuário por email"""
        result = self.db.table('users').select('*').eq('email', email).execute()
        return result.data[0] if result.data else None
    
    def get_by_id(self, user_id: str) -> Optional[dict]:
        """Busca usuário por ID"""
        result = self.db.table('users').select('*').eq('id', user_id).execute()
        return result.data[0] if result.data else None
    
    def update_last_ip(self, user_id: str, ip: str):
        """Atualiza último IP do usuário"""
        self.db.table('users').update({
            'last_ip': ip
        }).eq('id', user_id).execute()

class UsageModel:
    def __init__(self):
        self.db = Database.get_client()
    
    def get_current_month_usage(self, user_id: str) -> dict:
        """Obtém uso do mês atual"""
        current_month = datetime.now().strftime('%Y-%m')
        
        result = self.db.table('usage_credits').select('*').eq(
            'user_id', user_id
        ).eq('month_year', current_month).execute()
        
        if not result.data:
            # Cria registro se não existir
            return self.initialize_month(user_id)
        
        return result.data[0]
    
    def initialize_month(self, user_id: str) -> dict:
        """Inicializa uso do mês"""
        current_month = datetime.now().strftime('%Y-%m')
        
        # Busca plano do usuário
        user = self.db.table('users').select('current_plan').eq('id', user_id).execute()
        plan = user.data[0]['current_plan'] if user.data else 'free'
        
        # Busca limites do plano
        plan_data = self.db.table('plans').select('minutes_included').eq('id', plan).execute()
        minutes_limit = plan_data.data[0]['minutes_included'] if plan_data.data else 20
        
        data = {
            'user_id': user_id,
            'month_year': current_month,
            'minutes_limit': minutes_limit,
            'minutes_used': 0,
            'translation_minutes_used': 0
        }
        
        result = self.db.table('usage_credits').insert(data).execute()
        return result.data[0]
    
    def consume_minutes(self, user_id: str, minutes: float, translation_minutes: float = 0):
        """Consome minutos do usuário"""
        usage = self.get_current_month_usage(user_id)
        
        self.db.table('usage_credits').update({
            'minutes_used': usage['minutes_used'] + minutes,
            'translation_minutes_used': usage['translation_minutes_used'] + translation_minutes,
            'last_used_at': datetime.utcnow().isoformat()
        }).eq('id', usage['id']).execute()
    
    def can_use(self, user_id: str, required_minutes: float) -> tuple[bool, dict]:
        """Verifica se usuário pode usar X minutos"""
        usage = self.get_current_month_usage(user_id)
        
        available = usage['minutes_limit'] - usage['minutes_used']
        can_use = available >= required_minutes
        
        return can_use, {
            'available': available,
            'requested': required_minutes,
            'used': usage['minutes_used'],
            'limit': usage['minutes_limit']
        }

class JobModel:
    def __init__(self):
        self.db = Database.get_client()
    
    def create(self, user_id: str, file_type: str, source_language: str = None) -> dict:
        """Cria novo job"""
        data = {
            'user_id': user_id,
            'file_type': file_type,
            'source_language': source_language,
            'status': 'queued',
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.db.table('jobs').insert(data).execute()
        return result.data[0]
    
    def update_status(self, job_id: str, status: str, error: str = None):
        """Atualiza status do job"""
        data = {'status': status}
        
        if error:
            data['error_message'] = error
        
        if status == 'completed':
            data['completed_at'] = datetime.utcnow().isoformat()
        
        self.db.table('jobs').update(data).eq('id', job_id).execute()
    
    def update_job_details(self, job_id: str, **kwargs):
        """Atualiza detalhes do job"""
        self.db.table('jobs').update(kwargs).eq('id', job_id).execute()
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Busca job por ID"""
        result = self.db.table('jobs').select('*').eq('id', job_id).execute()
        return result.data[0] if result.data else None

class IPBlockModel:
    def __init__(self):
        self.db = Database.get_client()
    
    def is_blocked(self, ip: str) -> bool:
        """Verifica se IP está bloqueado"""
        result = self.db.table('blocked_ips').select('*').eq(
            'ip', ip
        ).gte('expires_at', datetime.utcnow().isoformat()).execute()
        
        return len(result.data) > 0
    
    def block_ip(self, ip: str, reason: str, hours: int = 24):
        """Bloqueia IP"""
        from datetime import timedelta
        
        expires_at = datetime.utcnow() + timedelta(hours=hours)
        
        self.db.table('blocked_ips').upsert({
            'ip': ip,
            'reason': reason,
            'blocked_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat()
        }).execute()
    
    def count_user_creations(self, ip: str, hours: int = 24) -> int:
        """Conta quantos usuários foram criados por este IP"""
        from datetime import timedelta
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        result = self.db.table('users').select('id').eq(
            'last_ip', ip
        ).gte('created_at', since.isoformat()).execute()
        
        return len(result.data)