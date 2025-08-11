"""
Mock do R2 Storage para desenvolvimento local
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import hashlib

class LocalStorage:
    """Simula R2 Storage usando sistema de arquivos local"""
    
    def __init__(self):
        self.base_path = Path("/storage/legendas-master/local_storage")
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def upload_file(self, file_path: str, user_id: str, file_type: str) -> Dict:
        """Simula upload copiando arquivo para storage local"""
        try:
            # Gera nome único
            file_hash = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()[:8]
            extension = os.path.splitext(file_path)[1]
            
            # Cria estrutura de pastas
            dest_dir = self.base_path / user_id / file_type
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Copia arquivo
            dest_path = dest_dir / f"{file_hash}{extension}"
            shutil.copy2(file_path, dest_path)
            
            # Gera "URL" local
            local_url = f"http://localhost:8000/local-storage/{user_id}/{file_type}/{file_hash}{extension}"
            
            return {
                'success': True,
                'key': f"{user_id}/{file_type}/{file_hash}{extension}",
                'url': local_url,
                'expires_in': 86400
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_download_url(self, object_key: str, expires_in: int = 86400) -> str:
        """Gera URL local para download"""
        return f"http://localhost:8000/local-storage/{object_key}"
    
    def delete_file(self, object_key: str) -> bool:
        """Remove arquivo do storage local"""
        try:
            file_path = self.base_path / object_key
            if file_path.exists():
                file_path.unlink()
            return True
        except:
            return False