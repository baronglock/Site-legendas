"""
Configuração e gerenciamento do Supabase - Versão Ajustada
"""
from supabase import create_client, Client
import os
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv
import asyncio

# Carregar variáveis de ambiente
load_dotenv()

# Pegar do .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("⚠️ Configure SUPABASE_URL e SUPABASE_ANON_KEY no arquivo .env!")

# Cliente global
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class Database:
    """Classe para gerenciar operações do banco"""
    
    @staticmethod
    async def create_user(email: str) -> Optional[Dict]:
        """Cria novo usuário ou retorna existente"""
        try:
            # Verificar se já existe
            existing = await Database.get_user_by_email(email)
            if existing:
                print(f"ℹ️ Usuário já existe: {email}")
                return existing
            
            # Criar novo usuário
            response = supabase.table('users').insert({
                'email': email,
                'current_plan': 'free',
                'is_active': True,
                'minutes_limit': 20
            }).execute()
            
            if response.data:
                user = response.data[0]
                print(f"✅ Usuário criado: {email} (ID: {user['id']})")
                
                # O trigger cria automaticamente os créditos do mês
                return user
            
            return None
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
            return None
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict]:
        """Busca usuário por email"""
        try:
            response = supabase.table('users').select("*").eq('email', email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Erro ao buscar usuário: {e}")
            return None
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict]:
        """Busca usuário por ID"""
        try:
            response = supabase.table('users').select("*").eq('id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Erro ao buscar usuário por ID: {e}")
            return None
    
    @staticmethod
    async def check_user_credits(user_id: str, required_minutes: int) -> bool:
        """Verifica se usuário tem créditos suficientes no mês atual"""
        try:
            current_month = datetime.now().strftime('%Y-%m')
            
            # Buscar uso do mês atual
            response = supabase.table('usage_credits').select("*").eq(
                'user_id', user_id
            ).eq('month_year', current_month).execute()
            
            if not response.data:
                # Não tem registro do mês = pode usar (trigger criará)
                return True
            
            usage = response.data[0]
            available = float(usage['minutes_limit']) - float(usage['minutes_used'])
            
            print(f"📊 Créditos: {available:.1f} disponíveis, {required_minutes} necessários")
            return available >= required_minutes
            
        except Exception as e:
            print(f"❌ Erro ao verificar créditos: {e}")
            return False
    
    @staticmethod
    async def create_job(job_data: Dict) -> Optional[Dict]:
        """Cria novo job"""
        try:
            # Garantir que temos os campos necessários
            job_data.setdefault('whisper_model', 'small')
            job_data.setdefault('translation_model', 'googletrans')
            
            response = supabase.table('jobs').insert(job_data).execute()
            
            if response.data:
                print(f"✅ Job criado: {job_data['id']}")
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Erro ao criar job: {e}")
            return None
    
    @staticmethod
    async def update_job(job_id: str, updates: Dict) -> Optional[Dict]:
        """Atualiza job"""
        try:
            # Se estiver completando, adicionar timestamp
            if updates.get('status') == 'completed':
                updates['completed_at'] = datetime.utcnow().isoformat()
            
            response = supabase.table('jobs').update(updates).eq('id', job_id).execute()
            
            if response.data:
                print(f"✅ Job atualizado: {job_id} -> {updates.get('status', '?')}")
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Erro ao atualizar job: {e}")
            return None
    
    @staticmethod
    async def get_job(job_id: str) -> Optional[Dict]:
        """Busca job por ID"""
        try:
            response = supabase.table('jobs').select("*").eq('id', job_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Erro ao buscar job: {e}")
            return None
    
    @staticmethod
    async def get_user_jobs(user_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Lista jobs do usuário"""
        try:
            response = supabase.table('jobs').select("*").eq(
                'user_id', user_id
            ).order(
                'created_at', desc=True
            ).range(offset, offset + limit - 1).execute()
            
            return response.data or []
        except Exception as e:
            print(f"❌ Erro ao listar jobs: {e}")
            return []
    
    @staticmethod
    async def update_user_usage(user_id: str, minutes: int, job_id: str = None) -> bool:
        """Atualiza minutos usados (usando a função SQL)"""
        try:
            current_month = datetime.now().strftime('%Y-%m')
            
            # Usar RPC para chamar a função SQL
            response = supabase.rpc('update_monthly_usage', {
                'p_user_id': user_id,
                'p_minutes': minutes
            }).execute()
            
            # Criar log de uso
            if job_id:
                supabase.table('usage_logs').insert({
                    'user_id': user_id,
                    'job_id': job_id,
                    'action': 'process',
                    'minutes_used': minutes
                }).execute()
            
            print(f"✅ Uso atualizado: +{minutes} minutos para usuário {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao atualizar uso: {e}")
            return False
    
    @staticmethod
    async def get_user_stats(user_id: str) -> Dict:
        """Retorna estatísticas do usuário do mês atual"""
        try:
            current_month = datetime.now().strftime('%Y-%m')
            
            # Buscar dados do usuário
            user = await Database.get_user_by_id(user_id)
            if not user:
                return {}
            
            # Buscar uso do mês
            usage_response = supabase.table('usage_credits').select("*").eq(
                'user_id', user_id
            ).eq('month_year', current_month).execute()
            
            usage = usage_response.data[0] if usage_response.data else {
                'minutes_used': 0,
                'minutes_limit': 20
            }
            
            # Contar jobs
            jobs_response = supabase.table('jobs').select(
                "id", count='exact'
            ).eq('user_id', user_id).execute()
            
            completed = supabase.table('jobs').select(
                "id", count='exact'
            ).eq('user_id', user_id).eq('status', 'completed').execute()
            
            return {
                'total_jobs': jobs_response.count or 0,
                'completed_jobs': completed.count or 0,
                'minutes_used': float(usage.get('minutes_used', 0)),
                'minutes_limit': float(usage.get('minutes_limit', 20)),
                'minutes_available': float(usage.get('minutes_limit', 20)) - float(usage.get('minutes_used', 0)),
                'current_month': current_month,
                'plan': user.get('current_plan', 'free')
            }
            
        except Exception as e:
            print(f"❌ Erro ao buscar estatísticas: {e}")
            return {
                'total_jobs': 0,
                'completed_jobs': 0,
                'minutes_used': 0,
                'minutes_limit': 20,
                'minutes_available': 20
            }
    
    @staticmethod
    async def check_ip_blocked(ip: str) -> bool:
        """Verifica se IP está bloqueado"""
        try:
            response = supabase.table('blocked_ips').select("*").eq(
                'ip', ip
            ).gt('expires_at', datetime.utcnow().isoformat()).execute()
            
            return len(response.data) > 0
        except:
            return False
    
    @staticmethod
    async def create_referral(referrer_id: str, referred_email: str) -> bool:
        """Cria referral"""
        try:
            response = supabase.table('referrals').insert({
                'referrer_user_id': referrer_id,
                'referred_email': referred_email,
                'bonus_minutes': 10
            }).execute()
            
            return response.data is not None
        except:
            return False

# Instância global
db = Database()