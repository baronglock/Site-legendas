"""
Otimizador de traduções - Versão FINAL para produção
Traduz arquivos de qualquer tamanho com divisão inteligente
"""
from deep_translator import GoogleTranslator
from pathlib import Path
import json
import time
from typing import List, Dict, Optional
from services.smart_translator import smart_translator


class TranslationOptimizer:
    def __init__(self):

        self.cache = {}
        self.calls_count = 0
        self.last_reset = time.time()
        self.MAX_CHARS_PER_CALL = 4000
    
    def translate_file_optimized(self, job_id: str, target_language: str = "pt") -> bool:
        """
        Tradução inteligente - detecta tamanho e divide se necessário
        VERSÃO FINAL PARA PRODUÇÃO
        """
        try:
            # 1. CARREGAR SEGMENTOS
            json_path = Path(f"/tmp/subtitle-ai/subtitles/{job_id}.json")

            with open(json_path, 'r', encoding='utf-8') as f:
                segments = json.load(f)
            
            # 2. ANALISAR TAMANHO TOTAL
            total_chars = sum(len(seg['text']) for seg in segments)
            total_segments = len(segments)
            
            print(f"\n📊 Análise do arquivo:")
            print(f"   - Segmentos: {total_segments}")
            print(f"   - Caracteres: {total_chars}")
            print(f"   - Tamanho estimado: {total_chars/150:.1f} minutos de vídeo")
            
            # 3. DECIDIR ESTRATÉGIA
            if total_chars <= self.MAX_CHARS_PER_CALL:
                # Arquivo pequeno - traduzir tudo de uma vez
                print("   ➡️ Estratégia: Tradução única")
                translated_segments = self._translate_single_call(segments, target_language)
            else:
                # Arquivo grande - dividir em chunks
                num_chunks = (total_chars // self.MAX_CHARS_PER_CALL) + 1
                print(f"   ➡️ Estratégia: Dividir em {num_chunks} blocos")
                translated_segments = self._translate_in_chunks(segments, target_language)
            
            # 4. SALVAR RESULTADOS
            if translated_segments:
                self._save_translated_files(job_id, translated_segments, target_language)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Erro na tradução: {e}")
            return False
    
    def _translate_single_call(self, segments: List[Dict], target_lang: str) -> List[Dict]:
        """Traduz tudo em uma única chamada (arquivos pequenos)"""
        try:
            # Combinar textos
            texts = [seg['text'] for seg in segments]
            combined = "\n[[[SEG]]]\n".join(texts)
            
            print(f"   📤 Traduzindo {len(texts)} segmentos em 1 chamada...")
            
            # Traduzir
            translator = GoogleTranslator(source='auto', target=target_lang)
            result_text = smart_translator.translate(combined, target_lang=target_lang)

            translated_texts = result_text.split("\n[[[SEG]]]\n")

            # Verificar integridade
            if len(translated_texts) != len(texts):
                print(f"   ⚠️ Ajustando: {len(texts)} → {len(translated_texts)}")
                while len(translated_texts) < len(texts):
                    translated_texts.append("")
            
            # Criar segmentos traduzidos
            translated_segments = []
            for i, seg in enumerate(segments):
                translated_segments.append({
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': translated_texts[i] if i < len(translated_texts) else seg['text']
                })
            
            print("   ✅ Tradução concluída!")
            return translated_segments
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            return None
    
    def _translate_in_chunks(self, segments: List[Dict], target_lang: str) -> List[Dict]:
        """Traduz em múltiplos chunks (arquivos grandes)"""
        try:
            # Criar chunks inteligentes
            chunks = self._create_smart_chunks(segments)
            translated_segments = segments.copy()
            
            # Traduzir cada chunk
            for i, chunk in enumerate(chunks):
                print(f"   📤 Traduzindo bloco {i+1}/{len(chunks)}...")
                
                # Extrair dados do chunk
                indices = [item[0] for item in chunk]
                texts = [item[1] for item in chunk]
                
                # Combinar e traduzir
                combined = "\n[[[SEG]]]\n".join(texts)
                
                try:
                    translator = GoogleTranslator(source='auto', target=target_lang)
                    result_text = translator.translate(combined)
                    translated_texts = result_text.split("\n[[[SEG]]]\n")
                    
                    # Aplicar traduções
                    for idx, trans_text in zip(indices, translated_texts):
                        translated_segments[idx]['text'] = trans_text
                    
                    # Pequena pausa entre chunks (evitar rate limit)
                    if i < len(chunks) - 1:
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"   ⚠️ Erro no bloco {i+1}: {e}")
                    # Continuar com próximo chunk
            
            print("   ✅ Todos os blocos traduzidos!")
            return translated_segments
            
        except Exception as e:
            print(f"   ❌ Erro geral: {e}")
            return None
    
    def _create_smart_chunks(self, segments: List[Dict]) -> List[List[tuple]]:
        """Cria chunks inteligentes respeitando limites"""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for i, seg in enumerate(segments):
            text = seg['text']
            # +10 para o separador [[[SEG]]]
            text_size = len(text) + 10
            
            # Se adicionar este texto ultrapassar o limite
            if current_size + text_size > self.MAX_CHARS_PER_CALL and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [(i, text)]
                current_size = text_size
            else:
                current_chunk.append((i, text))
                current_size += text_size
        
        # Adicionar último chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Estatísticas dos chunks
        chunk_sizes = [sum(len(item[1]) for item in chunk) for chunk in chunks]
        print(f"   📊 Chunks criados: {len(chunks)}")
        print(f"   📏 Tamanhos: {chunk_sizes}")
        
        return chunks
    
    def _save_translated_files(self, job_id: str, segments: List[Dict], target_lang: str):
        """Salva arquivos traduzidos em múltiplos formatos"""
        try:
            # Definir e garantir que o diretório existe
            base_path = Path("/tmp/subtitle-ai/subtitles")
            base_path.mkdir(parents=True, exist_ok=True)  # ← ADICIONAR ESTA LINHA
            
            # SRT
            srt_path = base_path / f"{job_id}_{target_lang}.srt"
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, seg in enumerate(segments, 1):
                    start = self._format_time_srt(seg['start'])
                    end = self._format_time_srt(seg['end'])
                    f.write(f"{i}\n{start} --> {end}\n{seg['text']}\n\n")
            
            # VTT
            vtt_path = base_path / f"{job_id}_{target_lang}.vtt"
            with open(vtt_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                for seg in segments:
                    start = self._format_time_vtt(seg['start'])
                    end = self._format_time_vtt(seg['end'])
                    f.write(f"{start} --> {end}\n{seg['text']}\n\n")
            
            # JSON
            json_path = base_path / f"{job_id}_{target_lang}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(segments, f, ensure_ascii=False, indent=2)
            
            print(f"\n   📁 Arquivos salvos:")
            print(f"      - {srt_path.name}")
            print(f"      - {vtt_path.name}")
            print(f"      - {json_path.name}")
            
        except Exception as e:
            print(f"   ❌ Erro ao salvar: {e}")
    
    def _format_time_srt(self, seconds: float) -> str:
        """Formata tempo para SRT (00:00:00,000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")
    
    def _format_time_vtt(self, seconds: float) -> str:
        """Formata tempo para VTT (00:00:00.000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

# Instância global
translation_optimizer = TranslationOptimizer()