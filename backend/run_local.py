#!/usr/bin/env python3
"""
Script para rodar o sistema localmente com configurações de teste
"""
import os
import sys
from pathlib import Path

# Configurar paths para storage
os.environ['WHISPER_MODEL_PATH'] = '/storage/legendas-master/models/whisper'
os.environ['HF_HOME'] = '/storage/legendas-master/models/huggingface'
os.environ['TORCH_HOME'] = '/storage/legendas-master/models/torch'

# Usar .env.development
os.environ['ENV_FILE'] = '.env.development'

# Criar diretórios necessários
paths = [
    '/storage/legendas-master/temp/videos',
    '/storage/legendas-master/temp/audio', 
    '/storage/legendas-master/temp/subtitles',
    '/storage/legendas-master/models/whisper',
    '/storage/legendas-master/local_storage/videos',
    '/storage/legendas-master/local_storage/subtitles',
]

for path in paths:
    Path(path).mkdir(parents=True, exist_ok=True)

print("🚀 Iniciando servidor local...")
print(f"📁 Modelos em: /storage/legendas-master/models/")
print(f"📁 Arquivos temporários em: /storage/legendas-master/temp/")
print(f"🌐 API em: http://localhost:8000")
print(f"🎨 Frontend em: http://localhost:3000")

# Rodar o servidor
os.system("python app.py")