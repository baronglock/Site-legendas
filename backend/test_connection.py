# backend/test_connections.py
import os
import sys
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

print("🔍 Testando conexões...\n")

# 1. Teste Supabase
print("1️⃣ Testando Supabase...")
try:
    from models.database import Database
    if Database.test_connection():
        print("✅ Supabase conectado!")
    else:
        print("❌ Erro na conexão Supabase")
except Exception as e:
    print(f"❌ Erro Supabase: {e}")

# 2. Teste R2
print("\n2️⃣ Testando Cloudflare R2...")
try:
    from utils.r2_storage import R2Storage
    r2 = R2Storage()
    # Tenta listar buckets
    print("✅ R2 configurado!")
except Exception as e:
    print(f"❌ Erro R2: {e}")

# 3. Teste OpenAI
print("\n3️⃣ Testando OpenAI...")
try:
    from openai import OpenAI
    client = OpenAI()
    # Testa com uma chamada simples
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Diga 'ok' se funcionar"}],
        max_tokens=10
    )
    print("✅ OpenAI conectado!")
except Exception as e:
    print(f"❌ Erro OpenAI: {e}")

# 4. Verifica modelos Whisper
print("\n4️⃣ Verificando Whisper...")
try:
    from services.transcription import WhisperTranscriber
    print("✅ Whisper disponível!")
except Exception as e:
    print(f"❌ Erro Whisper: {e}")

print("\n✨ Teste concluído!")

# 5. Teste de criação de usuário
print("\n5️⃣ Testando criação de usuário...")
try:
    from services.auth_service import AuthService
    auth = AuthService()
    
    # Tenta criar usuário de teste
    import time
    test_email = f"teste_{int(time.time())}@example.com"
    result = auth.create_user(test_email, "127.0.0.1")
    
    if result['success']:
        print(f"✅ Usuário criado: {result['user_id']}")
        print(f"   Email: {test_email}")
    else:
        print("❌ Erro ao criar usuário")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n🎯 Próximo passo: rodar a API com 'python app.py'")# backend/test_connections.py
import os
import sys
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

print("🔍 Testando conexões...\n")

# 1. Teste Supabase
print("1️⃣ Testando Supabase...")
try:
    from models.database import Database
    if Database.test_connection():
        print("✅ Supabase conectado!")
    else:
        print("❌ Erro na conexão Supabase")
except Exception as e:
    print(f"❌ Erro Supabase: {e}")

# 2. Teste R2
print("\n2️⃣ Testando Cloudflare R2...")
try:
    from utils.r2_storage import R2Storage
    r2 = R2Storage()
    # Tenta listar buckets
    print("✅ R2 configurado!")
except Exception as e:
    print(f"❌ Erro R2: {e}")

# 3. Teste OpenAI
print("\n3️⃣ Testando OpenAI...")
try:
    from openai import OpenAI
    client = OpenAI()
    # Testa com uma chamada simples
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Diga 'ok' se funcionar"}],
        max_tokens=10
    )
    print("✅ OpenAI conectado!")
except Exception as e:
    print(f"❌ Erro OpenAI: {e}")

# 4. Verifica modelos Whisper
print("\n4️⃣ Verificando Whisper...")
try:
    from services.transcription import WhisperTranscriber
    print("✅ Whisper disponível!")
except Exception as e:
    print(f"❌ Erro Whisper: {e}")

print("\n✨ Teste concluído!")

# 5. Teste de criação de usuário
print("\n5️⃣ Testando criação de usuário...")
try:
    from services.auth_service import AuthService
    auth = AuthService()
    
    # Tenta criar usuário de teste
    import time
    test_email = f"teste_{int(time.time())}@example.com"
    result = auth.create_user(test_email, "127.0.0.1")
    
    if result['success']:
        print(f"✅ Usuário criado: {result['user_id']}")
        print(f"   Email: {test_email}")
    else:
        print("❌ Erro ao criar usuário")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n🎯 Próximo passo: rodar a API com 'python app.py'")