# workers/job_processor.py
import os
import tempfile
import requests
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Imports dos serviços
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.transcription import WhisperTranscriber
from services.translator_pro import AISubtitleTranslator
from services.subtitle_generator import SubtitleGenerator
from models.database import Database, JobModel, UsageModel

class JobProcessor:
    def __init__(self):
        self.db = Database.get_client()
        self.job_model = JobModel()
        self.usage_model = UsageModel()
        self.subtitle_generator = SubtitleGenerator()
        self.transcribers = {}  # Cache de modelos
        self.temp_dir = tempfile.gettempdir()
    
    def update_job_status(self, job_id: str, status: str, error: str = None):
        """Atualiza status do job no banco"""
        try:
            self.job_model.update_status(job_id, status, error)
        except Exception as e:
            print(f"Erro ao atualizar status: {e}")
    
    def update_job_complete(self, job_id: str, data: Dict):
        """Atualiza job como completo com todos os dados"""
        try:
            data["completed_at"] = datetime.utcnow().isoformat()
            self.job_model.update_job_details(job_id, **data)
        except Exception as e:
            print(f"Erro ao atualizar job completo: {e}")
    
    def download_audio_from_r2(self, audio_url: str, job_id: str) -> Optional[str]:
        """Baixa áudio do R2 para arquivo temporário"""
        try:
            audio_path = os.path.join(self.temp_dir, f"{job_id}.wav")
            
            # Download com streaming
            response = requests.get(audio_url, stream=True)
            response.raise_for_status()
            
            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return audio_path
            
        except Exception as e:
            print(f"Erro no download: {e}")
            return None
    
    def get_transcriber(self, model_name: str) -> WhisperTranscriber:
        """Obtém ou cria transcritor (com cache)"""
        if model_name not in self.transcribers:
            self.transcribers[model_name] = WhisperTranscriber(model_name)
        return self.transcribers[model_name]
    
    def transcribe_audio(self, audio_path: str, language: str, model_name: str) -> Dict:
        """Transcreve áudio usando Whisper"""
        try:
            transcriber = self.get_transcriber(model_name)
            result = transcriber.transcribe(audio_path, language)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def translate_segments(self, segments: List[Dict], source_lang: str, 
                         target_lang: str, model_name: str) -> List[Dict]:
        """Traduz segmentos usando GPT"""
        try:
            translator = AISubtitleTranslator(model=model_name)
            translated = translator.translate_segments(
                segments,
                source_lang,
                target_lang
            )
            return translated
        except Exception as e:
            print(f"Erro na tradução: {e}")
            return segments  # Retorna original em caso de erro
    
    def generate_and_upload_subtitles(self, segments: List[Dict], job_id: str, 
                                    user_id: str, is_translated: bool = False) -> Dict:
        """Gera legendas e faz upload para R2"""
        try:
            result = self.subtitle_generator.generate_subtitles(
                segments,
                job_id,
                user_id
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def consume_user_credits(self, user_id: str, transcription_minutes: float,
                           translation_minutes: float = 0):
        """Consome créditos do usuário"""
        try:
            self.usage_model.consume_minutes(
                user_id,
                transcription_minutes,
                translation_minutes
            )
        except Exception as e:
            print(f"Erro ao consumir créditos: {e}")

# Classe alternativa para processar jobs do banco (sem Redis)
class DatabaseJobPoller:
    """
    Alternativa ao Redis - busca jobs direto do Supabase
    """
    def __init__(self):
        self.db = Database.get_client()
        self.processor = JobProcessor()
        self.worker_id = os.getenv("RUNPOD_POD_ID", "local")
    
    def get_next_job(self) -> Optional[Dict]:
        """Busca próximo job na fila"""
        try:
            # Busca jobs com status 'queued' ordenados por prioridade e data
            result = self.db.table('jobs').select('*').eq(
                'status', 'queued'
            ).order('created_at', desc=False).limit(1).execute()
            
            if result.data:
                job = result.data[0]
                
                # Tenta marcar como 'processing' (evita concorrência)
                update = self.db.table('jobs').update({
                    'status': 'processing',
                    'worker_id': self.worker_id,
                    'started_at': datetime.utcnow().isoformat()
                }).eq('id', job['id']).eq('status', 'queued').execute()
                
                # Se conseguiu atualizar, retorna o job
                if update.data:
                    return job
            
            return None
            
        except Exception as e:
            print(f"Erro ao buscar job: {e}")
            return None
    
    def poll_and_process(self, interval: int = 10):
        """Loop principal - busca e processa jobs"""
        print(f"Worker {self.worker_id} iniciado. Polling a cada {interval}s...")
        
        while True:
            try:
                job = self.get_next_job()
                
                if job:
                    print(f"Processando job {job['id']}...")
                    
                    # Monta input no formato esperado
                    job_input = {
                        "job_id": job['id'],
                        "user_id": job['user_id'],
                        "audio_url": self._get_audio_url(job),
                        "source_language": job.get('source_language', 'auto'),
                        "target_language": job.get('target_language'),
                        "translate": bool(job.get('target_language')),
                        "whisper_model": self._get_whisper_model(job),
                        "translation_model": self._get_translation_model(job)
                    }
                    
                    # Processa usando o handler
                    from runpod_handler import handler
                    result = handler({"input": job_input})
                    
                    print(f"Job {job['id']} finalizado: {result}")
                else:
                    print("Nenhum job na fila")
                
            except Exception as e:
                print(f"Erro no polling: {e}")
            
            # Aguarda antes de buscar novamente
            time.sleep(interval)
    
    def _get_audio_url(self, job: Dict) -> str:
        """Gera URL do áudio no R2"""
        if job.get('r2_audio_key'):
            from utils.r2_storage import R2Storage
            r2 = R2Storage()
            return r2.generate_download_url(job['r2_audio_key'])
        return ""
    
    def _get_whisper_model(self, job: Dict) -> str:
        """Determina modelo Whisper baseado no plano"""
        # Busca plano do usuário
        user = self.db.table('users').select('current_plan').eq(
            'id', job['user_id']
        ).execute()
        
        if user.data:
            plan = user.data[0].get('current_plan', 'free')
            return Config.WHISPER_MODEL_PAID if plan != 'free' else Config.WHISPER_MODEL_FREE
        
        return Config.WHISPER_MODEL_FREE
    
    def _get_translation_model(self, job: Dict) -> str:
        """Determina modelo de tradução baseado no plano"""
        user = self.db.table('users').select('current_plan').eq(
            'id', job['user_id']
        ).execute()
        
        if user.data:
            plan = user.data[0].get('current_plan', 'free')
            return Config.TRANSLATION_MODEL_PAID if plan != 'free' else Config.TRANSLATION_MODEL_FREE
        
        return Config.TRANSLATION_MODEL_FREE

# Para rodar localmente sem RunPod
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        # Modo polling (busca jobs do banco)
        poller = DatabaseJobPoller()
        poller.poll_and_process()
    else:
        print("Use: python job_processor.py poll")