# backend/test_api.py
import requests
import time
import json

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

print("🧪 Testando API...\n")

# 1. Teste root
print("1️⃣ Testando endpoint raiz...")
response = requests.get(BASE_URL)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)[:200]}...\n")

# 2. Teste health
print("2️⃣ Testando health check...")
response = requests.get(f"{BASE_URL}/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# 3. Teste registro
print("3️⃣ Testando registro de usuário...")
test_email = f"test_{int(time.time())}@example.com"
register_data = {
    "email": test_email
}
response = requests.post(f"{API_URL}/auth/register", json=register_data)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    token = data['access_token']
    user_id = data['user_id']
    print(f"✅ Usuário criado!")
    print(f"   Token: {token[:50]}...")
    print(f"   User ID: {user_id}")
    
    # 4. Teste autenticação
    print("\n4️⃣ Testando endpoint autenticado...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/auth/me", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # 5. Teste limites de uso
    print("\n5️⃣ Testando limites de uso...")
    response = requests.get(f"{API_URL}/user/usage", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:300]}...")
    
else:
    print(f"❌ Erro no registro: {response.text}")

print("\n✅ Testes básicos concluídos!")
print("\n📝 Próximos testes manuais:")
print("   - POST /api/v1/subtitle/upload (precisa de arquivo)")
print("   - POST /api/v1/subtitle/url (com URL de vídeo)")
print("   - GET /api/v1/payment/plans")

# Exemplo de como testar upload
print("\n💡 Exemplo de teste de upload com curl:")
print("""
curl -X POST http://localhost:8000/api/v1/subtitle/upload \\
  -H "Authorization: Bearer SEU_TOKEN" \\
  -F "file=@video.mp4" \\
  -F "source_language=auto" \\
  -F "target_language=pt" \\
  -F "translate=true"
""")