"""
Sistema inteligente de tradução com fallback automático
Alterna entre serviços quando atinge limites
"""
from deep_translator import GoogleTranslator, YandexTranslator, LibreTranslator
import time
from typing import Optional, List
import random

class SmartTranslator:
    def __init__(self):
        # Contadores de uso por serviço
        self.usage_counts = {
            'google': 0,
            'yandex': 0,
            'libre': 0
        }
        
        # Limites por hora (conservadores para segurança)
        self.hourly_limits = {
            'google': 150,  # Google Translate
            'yandex': 100,  # Yandex
            'libre': 500    # LibreTranslate (se tiver servidor próprio)
        }
        
        # Timestamps do último reset
        self.last_reset = time.time()
        
        # Cache de tradutores
        self.translators = {
            'google': lambda src, tgt: GoogleTranslator(source=src, target=tgt),
            'yandex': lambda src, tgt: YandexTranslator(source=src, target=tgt),

            # LibreTranslate precisa de URL do servidor
            # 'libre': lambda src, tgt: LibreTranslate(source=src, target=tgt, base_url="https://libretranslate.com/")
        }
        
        # Ordem de preferência
        self.priority = ['google', 'yandex']  # Google primeiro, Yandex como backup
        
    def translate(self, text: str, target_lang: str = 'pt', source_lang: str = 'auto') -> Optional[str]:
        """
        Traduz texto usando o melhor serviço disponível
        """
        # Reset contadores a cada hora
        self._check_reset_counters()
        
        # Tentar cada serviço na ordem de prioridade
        for service in self.priority:
            if self._can_use_service(service):
                result = self._try_translate(service, text, source_lang, target_lang)
                if result is not None:
                    return result
        
        # Se todos falharam, tentar qualquer um com delay
        print("⚠️ Todos os serviços no limite! Tentando com delay...")
        time.sleep(2)  # Espera 2 segundos
        
        # Última tentativa com serviço aleatório
        service = random.choice(self.priority)
        return self._try_translate(service, text, source_lang, target_lang, force=True)
    
    def translate_batch(self, texts: List[str], target_lang: str = 'pt', source_lang: str = 'auto') -> List[str]:
        """
        Traduz múltiplos textos distribuindo entre serviços
        """
        self._check_reset_counters()
        results = []
        
        # Distribuir textos entre serviços disponíveis
        available_services = [s for s in self.priority if self._can_use_service(s)]
        
        if not available_services:
            print("⚠️ Nenhum serviço disponível!")
            available_services = self.priority  # Forçar uso
        
        for i, text in enumerate(texts):
            # Alternar entre serviços para distribuir carga
            service = available_services[i % len(available_services)]
            
            result = self._try_translate(service, text, source_lang, target_lang)
            results.append(result if result else text)
            
            # Pequeno delay entre traduções
            if i < len(texts) - 1:
                time.sleep(0.1)
        
        return results
    
    def _try_translate(self, service: str, text: str, source_lang: str, target_lang: str, force: bool = False) -> Optional[str]:
        """
        Tenta traduzir com um serviço específico
        """
        try:
            print(f"   🔄 Usando {service.upper()} para tradução...")
            
            # Criar tradutor
            if service == 'google':
                # Google aceita 'auto' como source
                translator = GoogleTranslator(source=source_lang, target=target_lang)
            elif service == 'yandex':
                # Yandex precisa de código de idioma específico
                src = 'en' if source_lang == 'auto' else source_lang
                translator = YandexTranslate(source=src, target=target_lang)
            else:
                return None
            
            # Traduzir
            result = translator.translate(text)
            
            # Incrementar contador se não for forçado
            if not force:
                self.usage_counts[service] += 1
            
            print(f"   ✅ {service.upper()} traduziu com sucesso!")
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Detectar se é limite de rate
            if any(word in error_msg for word in ['rate', 'limit', '429', 'quota']):
                print(f"   ⚠️ {service.upper()} atingiu limite!")
                self.usage_counts[service] = self.hourly_limits[service]  # Marcar como cheio
            else:
                print(f"   ❌ Erro no {service}: {e}")
            
            return None
    
    def _can_use_service(self, service: str) -> bool:
        """
        Verifica se pode usar um serviço
        """
        return self.usage_counts.get(service, 0) < self.hourly_limits.get(service, 0)
    
    def _check_reset_counters(self):
        """
        Reset contadores a cada hora
        """
        current_time = time.time()
        if current_time - self.last_reset > 3600:  # 1 hora
            print("🔄 Resetando contadores de uso...")
            self.usage_counts = {k: 0 for k in self.usage_counts}
            self.last_reset = current_time
    
    def get_status(self) -> dict:
        """
        Retorna status dos serviços
        """
        self._check_reset_counters()
        return {
            service: {
                'used': self.usage_counts[service],
                'limit': self.hourly_limits[service],
                'available': self.hourly_limits[service] - self.usage_counts[service],
                'percentage': (self.usage_counts[service] / self.hourly_limits[service] * 100)
            }
            for service in self.priority
        }

# Instância global
smart_translator = SmartTranslator()