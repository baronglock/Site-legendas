# backend/utils/rate_limiter.py
import redis
from typing import Tuple
from datetime import datetime, timedelta
from config import Config

class RateLimiter:
    def __init__(self):
        self.redis_client = redis.from_url(Config.REDIS_URL)
        
        # Limites por tipo
        self.limits = {
            'api_calls': {
                'free': (100, 3600),      # 100 calls por hora
                'paid': (1000, 3600),     # 1000 calls por hora
                'enterprise': (10000, 3600)  # 10k calls por hora
            },
            'uploads': {
                'free': (3, 86400),       # 3 uploads por dia
                'paid': (50, 86400),      # 50 uploads por dia
                'enterprise': (1000, 86400)  # 1000 uploads por dia
            },
            'transcriptions': {
                'free': (5, 3600),        # 5 por hora
                'paid': (50, 3600),       # 50 por hora
                'enterprise': (500, 3600)  # 500 por hora
            }
        }
    
    def check_rate_limit(self, identifier: str, action_type: str, 
                        user_plan: str = 'free') -> Tuple[bool, dict]:
        """
        Verifica se ação está dentro do limite
        
        Returns:
            (allowed, info_dict)
        """
        # Pega limites para o tipo de ação e plano
        if action_type not in self.limits:
            return True, {'error': 'Tipo de ação desconhecido'}
        
        plan_limits = self.limits[action_type].get(user_plan, self.limits[action_type]['free'])
        limit, window = plan_limits
        
        # Chave Redis
        key = f"rate_limit:{action_type}:{identifier}"
        
        # Incrementa contador
        current = self.redis_client.incr(key)
        
        # Define expiração na primeira vez
        if current == 1:
            self.redis_client.expire(key, window)
        
        # Verifica limite
        if current > limit:
            # Pega TTL para saber quanto tempo falta
            ttl = self.redis_client.ttl(key)
            
            return False, {
                'allowed': False,
                'limit': limit,
                'current': current,
                'reset_in': ttl,
                'reset_at': datetime.utcnow() + timedelta(seconds=ttl)
            }
        
        return True, {
            'allowed': True,
            'limit': limit,
            'current': current,
            'remaining': limit - current
        }
    
    def reset_limit(self, identifier: str, action_type: str):
        """
        Reseta contador de limite
        """
        key = f"rate_limit:{action_type}:{identifier}"
        self.redis_client.delete(key)
    
    def get_all_limits(self, identifier: str, user_plan: str = 'free') -> dict:
        """
        Retorna status de todos os limites
        """
        status = {}
        
        for action_type in self.limits.keys():
            _, info = self.check_rate_limit(identifier, action_type, user_plan)
            status[action_type] = info
        
        return status
    
    def is_ip_flooding(self, ip: str, threshold: int = 10, window: int = 60) -> bool:
        """
        Verifica se IP está fazendo flood de requests
        """
        key = f"flood_check:{ip}"
        
        # Incrementa contador
        count = self.redis_client.incr(key)
        
        # Define expiração
        if count == 1:
            self.redis_client.expire(key, window)
        
        return count > threshold
    
    def add_to_blacklist(self, identifier: str, duration: int = 3600):
        """
        Adiciona identificador à blacklist temporária
        """
        key = f"blacklist:{identifier}"
        self.redis_client.set(key, 1, ex=duration)
    
    def is_blacklisted(self, identifier: str) -> bool:
        """
        Verifica se está na blacklist
        """
        key = f"blacklist:{identifier}"
        return self.redis_client.exists(key) > 0