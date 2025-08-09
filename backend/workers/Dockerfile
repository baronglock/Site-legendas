# workers/Dockerfile
FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

# Instala ffmpeg e outras dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /workspace

# Copia requirements primeiro (para cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código do backend (necessário para imports)
COPY ../backend /workspace/backend

# Copia workers
COPY . /workspace/workers

# Define variáveis de ambiente
ENV PYTHONPATH=/workspace/backend:$PYTHONPATH
ENV WHISPER_MODEL_PATH=/workspace/models

# Comando padrão do RunPod
CMD ["python", "-u", "/workspace/workers/runpod_handler.py"]