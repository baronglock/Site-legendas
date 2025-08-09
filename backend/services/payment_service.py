# backend/services/payment_service.py
import stripe
from typing import Dict, Optional
from datetime import datetime, timedelta
from config import Config
from models.database import Database

class PaymentService:
    def __init__(self):
        stripe.api_key = Config.STRIPE_SECRET_KEY
        self.db = Database.get_client()
        
        # Configuração de preços
        self.plans = {
            'starter': {
                'price_usd': 9.99,
                'minutes': 120,
                'name': 'Iniciante'
            },
            'pro': {
                'price_usd': 19.99,
                'minutes': 300,
                'name': 'Pro'
            },
            'premium': {
                'price_usd': 49.99,
                'minutes': 900,
                'name': 'Premium'
            },
            'enterprise': {
                'price_usd': 99.99,
                'minutes': 9999,
                'name': 'Enterprise'
            }
        }
        
        self.credit_packages = {
            '30min': {
                'price_usd': 4.99,
                'minutes': 30,
                'name': '30 minutos extras'
            },
            '60min': {
                'price_usd': 8.99,
                'minutes': 60,
                'name': '1 hora extra'
            },
            '180min': {
                'price_usd': 24.99,
                'minutes': 180,
                'name': '3 horas extras'
            }
        }
    
    def create_or_get_customer(self, user_id: str, email: str) -> str:
        """
        Cria ou obtém customer do Stripe
        """
        # Busca usuário
        user = self.db.table('users').select('stripe_customer_id').eq('id', user_id).execute()
        
        if user.data and user.data[0].get('stripe_customer_id'):
            return user.data[0]['stripe_customer_id']
        
        # Cria novo customer
        customer = stripe.Customer.create(
            email=email,
            metadata={'user_id': user_id}
        )
        
        # Salva no banco
        self.db.table('users').update({
            'stripe_customer_id': customer.id
        }).eq('id', user_id).execute()
        
        return customer.id
    
    def create_subscription(self, user_id: str, plan_id: str, customer_id: str) -> Dict:
        """
        Cria assinatura no Stripe
        """
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plano inválido: {plan_id}")
        
        # Cria price (ou use price_id pré-configurado)
        price = stripe.Price.create(
            unit_amount=int(plan['price_usd'] * 100),  # Centavos
            currency='usd',
            recurring={'interval': 'month'},
            product_data={'name': f"Plano {plan['name']}"}
        )
        
        # Cria assinatura
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': price.id}],
            metadata={'user_id': user_id, 'plan_id': plan_id}
        )
        
        return {
            'subscription_id': subscription.id,
            'status': subscription.status,
            'current_period_end': subscription.current_period_end
        }
    
    def create_one_time_payment(self, user_id: str, package_id: str, customer_id: str) -> Dict:
        """
        Cria pagamento único para créditos extras
        """
        package = self.credit_packages.get(package_id)
        if not package:
            raise ValueError(f"Pacote inválido: {package_id}")
        
        # Cria PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=int(package['price_usd'] * 100),  # Centavos
            currency='usd',
            customer=customer_id,
            metadata={
                'user_id': user_id,
                'package_id': package_id,
                'minutes': package['minutes']
            }
        )
        
        return {
            'payment_intent_id': intent.id,
            'client_secret': intent.client_secret,
            'amount': package['price_usd'],
            'minutes': package['minutes']
        }
    
    def process_successful_payment(self, payment_intent_id: str) -> bool:
        """
        Processa pagamento bem-sucedido
        """
        # Busca PaymentIntent
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status != 'succeeded':
            return False
        
        metadata = intent.metadata
        user_id = metadata.get('user_id')
        minutes = int(metadata.get('minutes', 0))
        
        if not user_id or not minutes:
            return False
        
        # Adiciona créditos
        current_month = datetime.now().strftime('%Y-%m')
        
        # Busca uso atual
        usage = self.db.table('usage_credits').select('*').eq(
            'user_id', user_id
        ).eq('month_year', current_month).execute()
        
        if usage.data:
            # Atualiza limite
            current_limit = usage.data[0]['minutes_limit']
            new_limit = current_limit + minutes
            
            self.db.table('usage_credits').update({
                'minutes_limit': new_limit
            }).eq('id', usage.data[0]['id']).execute()
        
        # Registra pagamento
        self.db.table('payments').insert({
            'user_id': user_id,
            'stripe_payment_id': payment_intent_id,
            'amount_usd': intent.amount / 100,
            'credits_minutes': minutes,
            'status': 'completed'
        }).execute()
        
        return True
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancela assinatura
        """
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            
            # Atualiza usuário para plano free
            # (implementar busca por subscription_id)
            
            return True
        except Exception as e:
            print(f"Erro ao cancelar assinatura: {e}")
            return False
    
    def get_subscription_status(self, subscription_id: str) -> Optional[Dict]:
        """
        Verifica status da assinatura
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return {
                'status': subscription.status,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'canceled_at': subscription.canceled_at
            }
        except:
            return None
    
    def calculate_usage_cost(self, minutes: float, plan: str = 'free') -> Dict:
        """
        Calcula custo real do uso (para métricas internas)
        """
        # Custos aproximados por minuto
        costs = {
            'gpu_whisper_base': 0.001,    # $0.001/min
            'gpu_whisper_large': 0.003,   # $0.003/min
            'translation_nano': 0.0001,   # $0.0001/min
            'translation_mini': 0.0005,   # $0.0005/min
            'storage_r2': 0.00001,        # $0.00001/min
        }
        
        # Calcula baseado no plano
        if plan == 'free':
            whisper_cost = costs['gpu_whisper_base'] * minutes
            translation_cost = costs['translation_nano'] * minutes
        else:
            whisper_cost = costs['gpu_whisper_large'] * minutes
            translation_cost = costs['translation_mini'] * minutes
        
        storage_cost = costs['storage_r2'] * minutes
        
        total_cost = whisper_cost + translation_cost + storage_cost
        
        return {
            'whisper_cost': round(whisper_cost, 4),
            'translation_cost': round(translation_cost, 4),
            'storage_cost': round(storage_cost, 4),
            'total_cost': round(total_cost, 4),
            'currency': 'USD'
        }