# backend/api/payment.py
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from typing import Optional
import stripe
from datetime import datetime, timedelta

from config import Config
from models.database import UserModel, Database
from api.auth import get_current_user

router = APIRouter(prefix="/payment", tags=["Payments"])

# Configura Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

# Inicializa modelos
user_model = UserModel()
db = Database.get_client()

# Preços em USD
PLANS = {
    'starter': {
        'name': 'Iniciante',
        'price': 9.99,
        'minutes': 120,
        'stripe_price_id': 'price_starter_id'  # Criar no Stripe
    },
    'pro': {
        'name': 'Pro',
        'price': 19.99,
        'minutes': 300,
        'stripe_price_id': 'price_pro_id'
    },
    'premium': {
        'name': 'Premium', 
        'price': 49.99,
        'minutes': 900,
        'stripe_price_id': 'price_premium_id'
    }
}

CREDIT_PACKAGES = {
    'pack_30': {
        'name': '30 minutos extras',
        'price': 4.99,
        'minutes': 30,
        'stripe_price_id': 'price_pack30_id'
    },
    'pack_60': {
        'name': '1 hora extra',
        'price': 8.99,
        'minutes': 60,
        'stripe_price_id': 'price_pack60_id'
    },
    'pack_180': {
        'name': '3 horas extras',
        'price': 24.99,
        'minutes': 180,
        'stripe_price_id': 'price_pack180_id'
    }
}

@router.get("/plans")
async def get_plans():
    """
    Lista planos disponíveis
    """
    return {
        "plans": PLANS,
        "credit_packages": CREDIT_PACKAGES,
        "currency": "USD"
    }

@router.post("/create-checkout-session")
async def create_checkout_session(
    plan_id: str,
    success_url: str,
    cancel_url: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cria sessão de checkout no Stripe
    """
    # Verifica se é plano ou pacote de créditos
    if plan_id in PLANS:
        price_id = PLANS[plan_id]['stripe_price_id']
        mode = 'subscription'
    elif plan_id in CREDIT_PACKAGES:
        price_id = CREDIT_PACKAGES[plan_id]['stripe_price_id']
        mode = 'payment'
    else:
        raise HTTPException(status_code=400, detail="Plano inválido")
    
    try:
        # Cria ou atualiza customer no Stripe
        if not current_user.get('stripe_customer_id'):
            customer = stripe.Customer.create(
                email=current_user['email'],
                metadata={'user_id': current_user['id']}
            )
            
            # Salva customer ID
            db.table('users').update({
                'stripe_customer_id': customer.id
            }).eq('id', current_user['id']).execute()
            
            customer_id = customer.id
        else:
            customer_id = current_user['stripe_customer_id']
        
        # Cria sessão de checkout
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1
            }],
            mode=mode,
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            metadata={
                'user_id': current_user['id'],
                'plan_id': plan_id
            }
        )
        
        return {
            'checkout_url': session.url,
            'session_id': session.id
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None)
):
    """
    Webhook do Stripe para processar eventos
    """
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Processa eventos
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_checkout_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        await handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        await handle_subscription_cancelled(subscription)
    
    return {"status": "success"}

async def handle_checkout_completed(session):
    """
    Processa checkout completo
    """
    user_id = session['metadata']['user_id']
    plan_id = session['metadata']['plan_id']
    
    # Se é assinatura
    if session['mode'] == 'subscription':
        subscription_id = session['subscription']
        
        # Atualiza plano do usuário
        db.table('users').update({
            'current_plan': plan_id,
            'stripe_subscription_id': subscription_id,
            'plan_expires_at': None  # Remove expiração para assinaturas ativas
        }).eq('id', user_id).execute()
        
        # Atualiza créditos do mês
        current_month = datetime.now().strftime('%Y-%m')
        minutes = PLANS[plan_id]['minutes']
        
        db.table('usage_credits').update({
            'minutes_limit': minutes
        }).eq('user_id', user_id).eq('month_year', current_month).execute()
    
    # Se é compra única de créditos
    else:
        package = CREDIT_PACKAGES[plan_id]
        
        # Adiciona créditos extras
        current_month = datetime.now().strftime('%Y-%m')
        usage = db.table('usage_credits').select('*').eq(
            'user_id', user_id
        ).eq('month_year', current_month).execute()
        
        if usage.data:
            current_limit = usage.data[0]['minutes_limit']
            new_limit = current_limit + package['minutes']
            
            db.table('usage_credits').update({
                'minutes_limit': new_limit
            }).eq('id', usage.data[0]['id']).execute()
    
    # Registra pagamento
    db.table('payments').insert({
        'user_id': user_id,
        'stripe_payment_id': session['payment_intent'],
        'amount_usd': session['amount_total'] / 100,  # Stripe usa centavos
        'credits_minutes': PLANS.get(plan_id, CREDIT_PACKAGES.get(plan_id))['minutes'],
        'status': 'completed'
    }).execute()

async def handle_subscription_updated(subscription):
    """
    Processa atualização de assinatura
    """
    customer_id = subscription['customer']
    
    # Busca usuário
    user = db.table('users').select('*').eq(
        'stripe_customer_id', customer_id
    ).execute()
    
    if not user.data:
        return
    
    user_id = user.data[0]['id']
    
    # Se assinatura está ativa
    if subscription['status'] == 'active':
        # Identifica plano pelo price_id
        price_id = subscription['items']['data'][0]['price']['id']
        plan_id = None
        
        for pid, plan in PLANS.items():
            if plan['stripe_price_id'] == price_id:
                plan_id = pid
                break
        
        if plan_id:
            db.table('users').update({
                'current_plan': plan_id
            }).eq('id', user_id).execute()

async def handle_subscription_cancelled(subscription):
    """
    Processa cancelamento de assinatura
    """
    customer_id = subscription['customer']
    
    # Busca usuário
    user = db.table('users').select('*').eq(
        'stripe_customer_id', customer_id
    ).execute()
    
    if not user.data:
        return
    
    user_id = user.data[0]['id']
    
    # Volta para plano free
    db.table('users').update({
        'current_plan': 'free',
        'stripe_subscription_id': None
    }).eq('id', user_id).execute()
    
    # Ajusta créditos para plano free
    current_month = datetime.now().strftime('%Y-%m')
    db.table('usage_credits').update({
        'minutes_limit': Config.FREE_MINUTES_LIMIT
    }).eq('user_id', user_id).eq('month_year', current_month).execute()

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user)
):
    """
    Cancela assinatura atual
    """
    if not current_user.get('stripe_subscription_id'):
        raise HTTPException(status_code=400, detail="Sem assinatura ativa")
    
    try:
        # Cancela no Stripe
        stripe.Subscription.delete(
            current_user['stripe_subscription_id']
        )
        
        return {"message": "Assinatura cancelada com sucesso"}
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/billing-portal")
async def create_billing_portal_session(
    return_url: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cria sessão do portal de billing do Stripe
    """
    if not current_user.get('stripe_customer_id'):
        raise HTTPException(status_code=400, detail="Sem conta de pagamento")
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user['stripe_customer_id'],
            return_url=return_url
        )
        
        return {'url': session.url}
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))