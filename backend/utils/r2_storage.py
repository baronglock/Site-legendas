# utils/r2_storage.py
import boto3
from botocore.config import Config as BotoConfig
from datetime import datetime, timedelta
import os
from typing import Dict, Optional
import hashlib

class R2Storage:
    def __init__(self):
        # Configurações do R2 (você pegará no dashboard do Cloudflare)
        self.account_id = os.getenv('R2_ACCOUNT_ID')
        self.access_key = os.getenv('R2_ACCESS_KEY')
        self.secret_key = os.getenv('R2_SECRET_KEY')
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'subtitle-temp')
        
        # Configura cliente S3 compatível
        self.s3 = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=BotoConfig(signature_version='s3v4'),
            region_name='auto'
        )
    
    def upload_file(self, file_path: str, user_id: str, file_type: str) -> Dict:
        """
        Upload arquivo para R2 com expiração em 24h
        """
        try:
            # Gera nome único
            file_hash = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()[:8]
            extension = os.path.splitext(file_path)[1]
            object_key = f"{user_id}/{file_type}/{file_hash}{extension}"
            
            # Metadata para auto-delete
            metadata = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'auto_delete': '24h'
            }
            
            # Upload
            with open(file_path, 'rb') as file:
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=file,
                    Metadata=metadata
                )
            
            # Gera URL temporária (24h)
            presigned_url = self.generate_download_url(object_key)
            
            return {
                'success': True,
                'key': object_key,
                'url': presigned_url,
                'expires_in': 24 * 3600
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_download_url(self, object_key: str, expires_in: int = 86400) -> str:
        """
        Gera URL assinada para download (padrão 24h)
        """
        return self.s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': object_key
            },
            ExpiresIn=expires_in
        )
    
    def delete_file(self, object_key: str) -> bool:
        """
        Deleta arquivo do R2
        """
        try:
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except:
            return False
    
    def cleanup_old_files(self):
        """
        Remove arquivos com mais de 24h (rodar via cron)
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Lista objetos
        paginator = self.s3.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket_name):
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                # Verifica idade do arquivo
                if obj['LastModified'].replace(tzinfo=None) < cutoff_time:
                    self.delete_file(obj['Key'])
                    print(f"Deleted old file: {obj['Key']}")

# Configuração no Cloudflare:
# 1. Vá em R2 no dashboard
# 2. Crie um bucket chamado "subtitle-temp"
# 3. Crie API tokens em "Manage R2 API Tokens"
# 4. Adicione as credenciais no .env:
#    R2_ACCOUNT_ID=seu_account_id
#    R2_ACCESS_KEY=sua_access_key
#    R2_SECRET_KEY=sua_secret_key