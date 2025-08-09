# backend/services/translator_pro.py
from typing import List, Dict, Optional
import os
import time
import json
from openai import OpenAI
from config import Config

class AISubtitleTranslator:
    """
    Tradutor profissional usando GPT-5 nano/mini para traduções contextuais
    """
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider
        
        if provider == "openai":
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            # Usa GPT-5 como você pediu!
            self.model = model or Config.TRANSLATION_MODEL_PAID  # gpt-5-mini por padrão
        else:
            raise ValueError("Provider deve ser 'openai'")
    
    def translate_segments(self, segments: List[Dict], 
                         source_lang: str = 'en', 
                         target_lang: str = 'pt',
                         video_context: str = "") -> List[Dict]:
        """
        Traduz segmentos com contexto completo para melhor qualidade
        """
        # Agrupa segmentos em blocos para tradução contextual
        blocks = self._group_segments_for_context(segments)
        translated_segments = []
        
        for i, block in enumerate(blocks):
            print(f"Traduzindo bloco {i+1}/{len(blocks)}...")
            
            # Prepara contexto do bloco
            block_text = self._prepare_block_text(block)
            
            # Traduz com IA
            translated_text = self._translate_with_ai(
                block_text, 
                source_lang, 
                target_lang,
                video_context
            )
            
            # Mapeia de volta para segmentos individuais
            translated_block = self._map_translation_to_segments(
                block, 
                translated_text
            )
            
            translated_segments.extend(translated_block)
            
            # Pequena pausa entre blocos para evitar rate limit
            if i < len(blocks) - 1:
                time.sleep(0.5)
        
        return translated_segments
    
    def _group_segments_for_context(self, segments: List[Dict], 
                                   max_chars: int = 2000) -> List[List[Dict]]:
        """
        Agrupa segmentos em blocos para manter contexto
        """
        blocks = []
        current_block = []
        current_chars = 0
        
        for segment in segments:
            segment_chars = len(segment['text'])
            
            # Se adicionar este segmento exceder o limite, cria novo bloco
            if current_chars + segment_chars > max_chars and current_block:
                blocks.append(current_block)
                current_block = []
                current_chars = 0
            
            current_block.append(segment)
            current_chars += segment_chars
        
        if current_block:
            blocks.append(current_block)
        
        return blocks
    
    def _prepare_block_text(self, block: List[Dict]) -> str:
        """
        Prepara texto do bloco com marcadores especiais
        """
        lines = []
        for i, segment in enumerate(block):
            # Marca cada segmento com ID único
            lines.append(f"[SEG{i}] {segment['text']}")
        
        return "\n".join(lines)
    
    def _translate_with_ai(self, text: str, source_lang: str, 
                        target_lang: str, video_context: str) -> str:
        """
        Traduz usando GPT-5 com instruções específicas
        """
        try:
            # Monta o prompt especializado
            system_prompt = f"""Você é um tradutor profissional especializado em legendas.
            
Traduza do {self._get_language_name(source_lang)} para o {self._get_language_name(target_lang)}.

REGRAS IMPORTANTES:
1. Mantenha os marcadores [SEG0], [SEG1], etc. EXATAMENTE como estão
2. Preserve o tom e registro do original
3. Use linguagem natural e fluente para legendas
4. Considere o contexto do vídeo: {video_context if video_context else 'vídeo educacional/profissional'}
5. Mantenha comprimento similar ao original (para sincronização)
6. Adapte expressões idiomáticas para equivalentes naturais
7. Para termos técnicos, use a tradução mais comum no Brasil
8. Evite traduções literais que soem artificiais

FORMATO: Retorne APENAS a tradução, mantendo uma linha por segmento."""

            user_prompt = f"Traduza mantendo os marcadores [SEG]:\n\n{text}"
            
            print(f"Traduzindo com modelo: {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            result = response.choices[0].message.content
            return result
                    
        except Exception as e:
            print(f"Erro na tradução: {type(e).__name__}: {str(e)}")
            raise e
    
    def _map_translation_to_segments(self, original_block: List[Dict], 
                                   translated_text: str) -> List[Dict]:
        """
        Mapeia tradução de volta para segmentos individuais
        """
        translated_lines = translated_text.strip().split('\n')
        translated_segments = []
        
        # Cria dicionário de traduções por ID
        translations = {}
        for line in translated_lines:
            if line.strip() and '[SEG' in line:
                # Extrai ID e texto
                start = line.find('[SEG') + 4
                end = line.find(']')
                if start > 3 and end > start:
                    seg_id = line[start:end]
                    text = line[end+1:].strip()
                    try:
                        translations[int(seg_id)] = text
                    except ValueError:
                        continue
        
        # Aplica traduções aos segmentos originais
        for i, segment in enumerate(original_block):
            translated_segment = segment.copy()
            
            if i in translations:
                translated_segment['text'] = translations[i]
                translated_segment['original_text'] = segment['text']
            else:
                # Fallback se não encontrar tradução
                print(f"Aviso: Tradução não encontrada para segmento {i}")
                translated_segment['text'] = segment['text']
            
            translated_segments.append(translated_segment)
        
        return translated_segments
    
    def _get_language_name(self, code: str) -> str:
        """
        Retorna nome completo do idioma
        """
        languages = {
            'en': 'inglês',
            'pt': 'português brasileiro',
            'pt-BR': 'português brasileiro',
            'es': 'espanhol',
            'fr': 'francês',
            'de': 'alemão',
            'it': 'italiano',
            'ja': 'japonês',
            'zh': 'chinês',
            'ru': 'russo',
            'ar': 'árabe',
            'hi': 'hindi'
        }
        return languages.get(code, code)
    
    def translate_srt_file(self, srt_content: str, source_lang: str = 'en', 
                           target_lang: str = 'pt') -> str:
        """
        Traduz arquivo SRT completo mantendo formatação
        """
        blocks = srt_content.strip().split('\n\n')
        translated_blocks = []
        
        # Agrupa blocos para tradução mais eficiente
        text_to_translate = []
        block_info = []
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                number = lines[0]
                timing = lines[1]
                text = ' '.join(lines[2:])
                
                text_to_translate.append(f"[BLOCK{len(block_info)}] {text}")
                block_info.append((number, timing))
            else:
                # Bloco inválido, mantém como está
                translated_blocks.append(block)
        
        # Traduz todos os textos de uma vez
        if text_to_translate:
            full_text = '\n'.join(text_to_translate)
            
            # Usa a tradução com IA já configurada
            translated_text = self._translate_with_ai(
                full_text,
                source_lang,
                target_lang,
                "Arquivo de legendas SRT"
            )
            
            # Mapeia de volta para blocos
            translated_lines = translated_text.strip().split('\n')
            
            for line in translated_lines:
                if line.strip() and '[BLOCK' in line:
                    # Extrai índice e texto
                    match = line.find(']')
                    if match > 0:
                        block_idx_str = line[line.find('[BLOCK')+6:match]
                        try:
                            block_idx = int(block_idx_str)
                            translated_text = line[match+1:].strip()
                            
                            if block_idx < len(block_info):
                                number, timing = block_info[block_idx]
                                translated_block = f"{number}\n{timing}\n{translated_text}"
                                translated_blocks.append(translated_block)
                        except ValueError:
                            continue
        
        return '\n\n'.join(translated_blocks)
    
    def translate_vtt_file(self, vtt_content: str, source_lang: str = 'en',
                          target_lang: str = 'pt') -> str:
        """
        Traduz arquivo VTT (similar ao SRT mas com header WEBVTT)
        """
        # Remove header WEBVTT
        lines = vtt_content.split('\n')
        header = []
        content_start = 0
        
        for i, line in enumerate(lines):
            if '-->' in line:
                content_start = max(0, i - 1)
                break
            header.append(line)
        
        # Pega só o conteúdo (sem header)
        srt_like_content = '\n'.join(lines[content_start:])
        
        # Traduz como SRT
        translated_content = self.translate_srt_file(srt_like_content, source_lang, target_lang)
        
        # Reconstrói com header VTT
        return '\n'.join(header) + '\n' + translated_content
    
    def translate_with_glossary(self, segments: List[Dict], 
                              glossary: Dict[str, str],
                              source_lang: str = 'en',
                              target_lang: str = 'pt') -> List[Dict]:
        """
        Traduz com glossário de termos específicos
        """
        # Adiciona glossário ao contexto
        glossary_text = "GLOSSÁRIO OBRIGATÓRIO:\n"
        for term, translation in glossary.items():
            glossary_text += f"- {term} → {translation}\n"
        
        # Modifica o prompt do sistema para incluir glossário
        system_prompt_addition = f"\n\n{glossary_text}\nUSE SEMPRE as traduções do glossário acima."
        
        # Procede com tradução normal mas com contexto do glossário
        return self.translate_segments(
            segments, 
            source_lang, 
            target_lang,
            video_context=system_prompt_addition
        )

class BatchAITranslator:
    """
    Versão otimizada para traduzir múltiplos vídeos com cache
    """
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self.translator = AISubtitleTranslator(provider, api_key)
        self.cache = {}
        self.cache_file = Path(os.getenv('TEMP_DIR', '/tmp')) / "translation_cache.json"
        self._load_cache()
    
    def _load_cache(self):
        """Carrega cache de traduções anteriores"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
    
    def _save_cache(self):
        """Salva cache de traduções"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def translate_with_cache(self, text: str, source_lang: str = 'en', 
                           target_lang: str = 'pt') -> str:
        """
        Traduz com cache para economizar tokens
        """
        # Gera chave de cache
        cache_key = f"{source_lang}:{target_lang}:{text[:50]}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Traduz se não estiver em cache
        segments = [{"text": text, "start": 0, "end": 1}]
        translated = self.translator.translate_segments(
            segments, source_lang, target_lang
        )
        
        if translated:
            result = translated[0]['text']
            self.cache[cache_key] = result
            self._save_cache()
            return result
        
        return text