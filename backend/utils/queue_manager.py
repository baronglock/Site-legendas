# backend/utils/queue_manager.py
import redis
import json
from typing import Dict, Optional, List
from datetime import datetime
from config import Config

class QueueManager:
    def __init__(self):
        # Conecta ao Redis
        self.redis_client = redis.from_url(Config.REDIS_URL)
        
        # Nomes das filas por prioridade
        self.queues = {
            'free': 'queue:free',
            'paid': 'queue:paid',
            'priority': 'queue:priority'
        }
    
    def add_job(self, job_data: Dict, user_plan: str = 'free') -> str:
        """
        Adiciona job à fila apropriada
        """
        # Define fila baseada no plano
        queue_name = self._get_queue_name(user_plan)
        
        # Adiciona timestamp
        job_data['queued_at'] = datetime.utcnow().isoformat()
        job_data['queue'] = queue_name
        
        # Serializa e adiciona à fila
        job_json = json.dumps(job_data)
        self.redis_client.lpush(queue_name, job_json)
        
        # Salva status do job
        self._save_job_status(job_data['job_id'], 'queued', queue_name)
        
        return job_data['job_id']
    
    def get_next_job(self) -> Optional[Dict]:
        """
        Pega próximo job respeitando prioridades
        """
        # Ordem de prioridade: priority > paid > free
        for queue_type in ['priority', 'paid', 'free']:
            queue_name = self.queues[queue_type]
            
            # Tenta pegar job da fila (FIFO)
            job_data = self.redis_client.rpop(queue_name)
            
            if job_data:
                job = json.loads(job_data)
                self._save_job_status(job['job_id'], 'processing')
                return job
        
        return None
    
    def get_queue_length(self, queue_type: str = 'all') -> Dict[str, int]:
        """
        Retorna tamanho das filas
        """
        if queue_type == 'all':
            lengths = {}
            for name, queue in self.queues.items():
                lengths[name] = self.redis_client.llen(queue)
            return lengths
        else:
            queue_name = self.queues.get(queue_type, queue_type)
            return {queue_type: self.redis_client.llen(queue_name)}
    
    def get_job_position(self, job_id: str) -> Optional[int]:
        """
        Retorna posição do job na fila
        """
        for queue_name in self.queues.values():
            # Pega todos os jobs da fila
            jobs = self.redis_client.lrange(queue_name, 0, -1)
            
            for i, job_data in enumerate(jobs):
                job = json.loads(job_data)
                if job.get('job_id') == job_id:
                    # Posição é invertida (FIFO)
                    return len(jobs) - i
        
        return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Remove job da fila
        """
        for queue_name in self.queues.values():
            # Pega todos os jobs
            jobs = self.redis_client.lrange(queue_name, 0, -1)
            
            for job_data in jobs:
                job = json.loads(job_data)
                if job.get('job_id') == job_id:
                    # Remove da fila
                    self.redis_client.lrem(queue_name, 1, job_data)
                    self._save_job_status(job_id, 'cancelled')
                    return True
        
        return False
    
    def _get_queue_name(self, user_plan: str) -> str:
        """
        Determina fila baseada no plano
        """
        if user_plan in ['enterprise', 'premium']:
            return self.queues['priority']
        elif user_plan in ['pro', 'starter']:
            return self.queues['paid']
        else:
            return self.queues['free']
    
    def _save_job_status(self, job_id: str, status: str, queue: str = None):
        """
        Salva status do job no Redis
        """
        key = f"job:status:{job_id}"
        data = {
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if queue:
            data['queue'] = queue
        
        self.redis_client.set(key, json.dumps(data))
        # Expira em 24 horas
        self.redis_client.expire(key, 86400)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Retorna status do job
        """
        key = f"job:status:{job_id}"
        data = self.redis_client.get(key)
        
        if data:
            return json.loads(data)
        
        return None
    
    def get_estimated_wait_time(self, queue_type: str) -> int:
        """
        Estima tempo de espera em minutos
        """
        queue_length = self.get_queue_length(queue_type)[queue_type]
        
        # Estimativas baseadas no tipo de fila
        avg_processing_time = {
            'free': 5,      # 5 min por job (hardware mais lento)
            'paid': 3,      # 3 min por job
            'priority': 2   # 2 min por job (hardware premium)
        }
        
        avg_time = avg_processing_time.get(queue_type, 5)
        return queue_length * avg_time