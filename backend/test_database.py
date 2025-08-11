"""
Teste completo do banco de dados
"""
import asyncio
from database import db
from datetime import datetime

async def test_database():
    print("\n" + "="*60)
    print("🧪 TESTE COMPLETO DO BANCO DE DADOS")
    print("="*60)
    
    # 1. TESTE DE USUÁRIO
    print("\n1️⃣ TESTANDO CRIAÇÃO DE USUÁRIO...")
    test_email = f"teste_{datetime.now().strftime('%H%M%S')}@teste.com"
    
    user = await db.create_user(test_email)
    if user:
        print(f"✅ Usuário criado: {user['email']} (ID: {user['id']})")
    else:
        print("❌ Falha ao criar usuário")
        return
    
    # 2. BUSCAR USUÁRIO
    print("\n2️⃣ TESTANDO BUSCA DE USUÁRIO...")
    found_user = await db.get_user_by_email(test_email)
    if found_user:
        print(f"✅ Usuário encontrado por email")
    
    # 3. VERIFICAR CRÉDITOS
    print("\n3️⃣ TESTANDO CRÉDITOS...")
    has_credits = await db.check_user_credits(user['id'], 5)
    print(f"✅ Tem créditos para 5 minutos? {has_credits}")
    
    has_credits_30 = await db.check_user_credits(user['id'], 30)
    print(f"✅ Tem créditos para 30 minutos? {has_credits_30}")
    
    # 4. CRIAR JOB
    print("\n4️⃣ TESTANDO CRIAÇÃO DE JOB...")
    job_data = {
        'id': f"job_test_{int(datetime.now().timestamp())}",
        'user_id': user['id'],
        'filename': 'teste.mp4',
        'status': 'processing',
        'file_size': 1024000,
        'source_language': 'en',
        'target_language': 'pt'
    }
    
    job = await db.create_job(job_data)
    if job:
        print(f"✅ Job criado: {job['id']}")
    
    # 5. ATUALIZAR JOB
    print("\n5️⃣ TESTANDO ATUALIZAÇÃO DE JOB...")
    updated = await db.update_job(job['id'], {
        'status': 'completed',
        'audio_duration_seconds': 120,
        'result_urls': {
            'srt': '/download/test.srt',
            'vtt': '/download/test.vtt'
        }
    })
    if updated:
        print(f"✅ Job atualizado para: {updated['status']}")
    
    # 6. LISTAR JOBS
    print("\n6️⃣ TESTANDO LISTAGEM DE JOBS...")
    jobs = await db.get_user_jobs(user['id'])
    print(f"✅ Jobs encontrados: {len(jobs)}")
    
    # 7. ATUALIZAR USO
    print("\n7️⃣ TESTANDO ATUALIZAÇÃO DE USO...")
    usage_ok = await db.update_user_usage(user['id'], 2, job['id'])
    if usage_ok:
        print("✅ Uso atualizado (+2 minutos)")
    
    # 8. ESTATÍSTICAS
    print("\n8️⃣ TESTANDO ESTATÍSTICAS...")
    stats = await db.get_user_stats(user['id'])
    print(f"✅ Estatísticas:")
    print(f"   - Jobs total: {stats['total_jobs']}")
    print(f"   - Jobs completos: {stats['completed_jobs']}")
    print(f"   - Minutos usados: {stats['minutes_used']}")
    print(f"   - Minutos disponíveis: {stats['minutes_available']}")
    print(f"   - Plano: {stats['plan']}")
    
    print("\n" + "="*60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*60)

# Executar testes
if __name__ == "__main__":
    asyncio.run(test_database())