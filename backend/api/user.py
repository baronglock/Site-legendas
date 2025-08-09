# backend/api/user.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta

from config import Config
from models.database import Database, JobModel, UsageModel
from utils.rate_limiter import RateLimiter
from api.auth import get_current_user

router = APIRouter(prefix="/user", tags=["User"])

# Inicializa serviços
db = Database.get_client()
job_model = JobModel()
usage_model = UsageModel()
rate_limiter = RateLimiter()

@router.get("/usage")
async def get_usage(current_user: dict = Depends(get_current_user)):
    """
    Retorna uso detalhado do usuário
    """
    user_id = current_user['id']
    
    # Uso do mês atual
    current_usage = usage_model.get_current_month_usage(user_id)
    
    # Histórico dos últimos 3 meses
    history = []
    for i in range(3):
        date = datetime.now() - timedelta(days=30 * i)
        month = date.strftime('%Y-%m')
        
        result = db.table('usage_credits').select('*').eq(
            'user_id', user_id
        ).eq('month_year', month).execute()
        
        if result.data:
            history.append({
                'month': month,
                'minutes_used': result.data[0]['minutes_used'],
                'minutes_limit': result.data[0]['minutes_limit'],
                'translation_minutes': result.data[0]['translation_minutes_used']
            })
    
    # Rate limits atuais
    rate_limits = rate_limiter.get_all_limits(user_id, current_user.get('current_plan', 'free'))
    
    return {
        'current_month': {
            'month': datetime.now().strftime('%Y-%m'),
            'minutes_used': current_usage['minutes_used'],
            'minutes_limit': current_usage['minutes_limit'],
            'minutes_available': current_usage['minutes_limit'] - current_usage['minutes_used'],
            'translation_minutes_used': current_usage['translation_minutes_used'],
            'percentage_used': (current_usage['minutes_used'] / current_usage['minutes_limit'] * 100) 
                              if current_usage['minutes_limit'] > 0 else 0
        },
        'history': history,
        'rate_limits': rate_limits
    }

@router.get("/jobs")
async def get_user_jobs(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Lista jobs do usuário
    """
    query = db.table('jobs').select('*').eq('user_id', current_user['id'])
    
    if status:
        query = query.eq('status', status)
    
    # Ordenar por data de criação (mais recente primeiro)
    query = query.order('created_at', desc=True)
    
    # Paginação
    query = query.range(offset, offset + limit - 1)
    
    result = query.execute()
    
    # Formata jobs
    jobs = []
    for job in result.data:
        job_data = {
            'id': job['id'],
            'status': job['status'],
            'created_at': job['created_at'],
            'completed_at': job.get('completed_at'),
            'source_language': job.get('source_language'),
            'target_language': job.get('target_language'),
            'duration_seconds': job.get('audio_duration_seconds'),
            'error': job.get('error_message')
        }
        
        # Se completado, adiciona URLs de download
        if job['status'] == 'completed' and (job.get('r2_subtitle_key') or job.get('r2_translated_key')):
            from utils.r2_storage import R2Storage
            r2 = R2Storage()
            
            job_data['downloads'] = {}
            
            if job.get('r2_subtitle_key'):
                job_data['downloads']['original'] = r2.generate_download_url(job['r2_subtitle_key'])
            
            if job.get('r2_translated_key'):
                job_data['downloads']['translated'] = r2.generate_download_url(job['r2_translated_key'])
        
        jobs.append(job_data)
    
    # Conta total
    count_result = db.table('jobs').select('count').eq('user_id', current_user['id']).execute()
    total = count_result.count if hasattr(count_result, 'count') else len(result.data)
    
    return {
        'jobs': jobs,
        'total': total,
        'limit': limit,
        'offset': offset
    }

@router.get("/stats")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """
    Estatísticas do usuário
    """
    user_id = current_user['id']
    
    # Total de transcrições
    total_jobs = db.table('jobs').select('count').eq('user_id', user_id).execute()
    
    # Jobs por status
    statuses = ['completed', 'failed', 'cancelled']
    stats_by_status = {}
    
    for status in statuses:
        count = db.table('jobs').select('count').eq(
            'user_id', user_id
        ).eq('status', status).execute()
        stats_by_status[status] = count.count if hasattr(count, 'count') else 0
    
    # Total de minutos processados
    completed_jobs = db.table('jobs').select('audio_duration_seconds').eq(
        'user_id', user_id
    ).eq('status', 'completed').execute()
    
    total_seconds = sum(job['audio_duration_seconds'] for job in completed_jobs.data if job.get('audio_duration_seconds'))
    total_minutes = total_seconds / 60
    
    # Idiomas mais usados
    language_stats = {}
    lang_results = db.table('jobs').select('source_language').eq(
        'user_id', user_id
    ).eq('status', 'completed').execute()
    
    for job in lang_results.data:
        lang = job.get('source_language', 'unknown')
        language_stats[lang] = language_stats.get(lang, 0) + 1
    
    # Tempo médio de processamento
    recent_jobs = db.table('jobs').select('created_at', 'completed_at').eq(
        'user_id', user_id
    ).eq('status', 'completed').order('created_at', desc=True).limit(20).execute()
    
    processing_times = []
    for job in recent_jobs.data:
        if job.get('created_at') and job.get('completed_at'):
            created = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
            completed = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
            processing_times.append((completed - created).total_seconds())
    
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    
    return {
        'total_jobs': total_jobs.count if hasattr(total_jobs, 'count') else 0,
        'jobs_by_status': stats_by_status,
        'total_minutes_processed': round(total_minutes, 1),
        'total_hours_processed': round(total_minutes / 60, 1),
        'languages_used': language_stats,
        'average_processing_time_seconds': round(avg_processing_time, 1),
        'member_since': current_user['created_at']
    }

@router.post("/referral")
async def create_referral(
    referred_email: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cria código de indicação
    """
    from utils.validators import Validators
    
    # Valida email
    if not Validators.is_valid_email(referred_email):
        raise HTTPException(status_code=400, detail="Email inválido")
    
    # Verifica se já foi indicado
    existing = db.table('referrals').select('id').eq(
        'referrer_user_id', current_user['id']
    ).eq('referred_email', referred_email).execute()
    
    if existing.data:
        raise HTTPException(status_code=400, detail="Email já indicado")
    
    # Cria indicação
    result = db.table('referrals').insert({
        'referrer_user_id': current_user['id'],
        'referred_email': referred_email,
        'bonus_minutes': 10  # 10 minutos de bônus
    }).execute()
    
    return {
        'message': 'Indicação criada com sucesso',
        'referral_id': result.data[0]['id'],
        'bonus_minutes': 10
    }

@router.get("/referrals")
async def get_referrals(current_user: dict = Depends(get_current_user)):
    """
    Lista indicações do usuário
    """
    result = db.table('referrals').select('*').eq(
        'referrer_user_id', current_user['id']
    ).order('created_at', desc=True).execute()
    
    referrals = []
    for ref in result.data:
        referrals.append({
            'email': ref['referred_email'],
            'created_at': ref['created_at'],
            'claimed': ref.get('claimed_at') is not None,
            'bonus_minutes': ref['bonus_minutes']
        })
    
    # Total de bônus ganhos
    claimed = [r for r in referrals if r['claimed']]
    total_bonus = sum(r['bonus_minutes'] for r in claimed)
    
    return {
        'referrals': referrals,
        'total_referrals': len(referrals),
        'total_claimed': len(claimed),
        'total_bonus_minutes': total_bonus
    }

@router.put("/settings")
async def update_settings(
    settings: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza configurações do usuário
    """
    # Campos permitidos para atualização
    allowed_fields = ['notification_email', 'preferred_language', 'timezone']
    
    update_data = {}
    for field in allowed_fields:
        if field in settings:
            update_data[field] = settings[field]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
    
    # Atualiza
    db.table('users').update(update_data).eq('id', current_user['id']).execute()
    
    return {
        'message': 'Configurações atualizadas com sucesso',
        'updated_fields': list(update_data.keys())
    }

@router.delete("/account")
async def delete_account(
    confirm: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Deleta conta do usuário (GDPR compliance)
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Por favor, confirme a exclusão da conta com confirm=true"
        )
    
    user_id = current_user['id']
    
    # Cancela assinatura se houver
    if current_user.get('stripe_subscription_id'):
        import stripe
        stripe.api_key = Config.STRIPE_SECRET_KEY
        
        try:
            stripe.Subscription.delete(current_user['stripe_subscription_id'])
        except:
            pass
    
    # Marca jobs como deletados (mantém por auditoria mas anonimiza)
    db.table('jobs').update({
        'user_id': None,
        'deleted_at': datetime.utcnow().isoformat()
    }).eq('user_id', user_id).execute()
    
    # Deleta dados pessoais
    db.table('users').delete().eq('id', user_id).execute()
    db.table('usage_credits').delete().eq('user_id', user_id).execute()
    db.table('referrals').delete().eq('referrer_user_id', user_id).execute()
    
    return {'message': 'Conta deletada com sucesso'}