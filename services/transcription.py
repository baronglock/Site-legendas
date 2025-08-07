import torch
from pathlib import Path
from typing import Dict, List, Optional
import json
from config import Config
import warnings
warnings.filterwarnings("ignore")

# Import do Whisper com tratamento de erro
try:
    import whisper
except ImportError:
    print("Erro ao importar Whisper. Instale com: pip install openai-whisper")
    raise

class WhisperTranscriber:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or Config.WHISPER_MODEL
        self.device = Config.WHISPER_DEVICE
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Carrega o modelo Whisper com otimizações"""
        print(f"Carregando modelo Whisper {self.model_name}...")
        
        # Verifica disponibilidade de CUDA
        if self.device == "cuda" and not torch.cuda.is_available():
            self.device = "cpu"
            print("CUDA não disponível, usando CPU")
        
        # Lista de modelos disponíveis
        available_models = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        
        if self.model_name not in available_models:
            print(f"Modelo {self.model_name} não encontrado. Usando 'base'")
            self.model_name = "base"
        
        try:
            self.model = whisper.load_model(
                self.model_name,
                device=self.device
            )
        except Exception as e:
            print(f"Erro ao carregar modelo {self.model_name}: {e}")
            print("Tentando modelo 'base'...")
            self.model = whisper.load_model("base", device=self.device)
        
        if self.device == "cuda":
            # Otimizações para GPU
            torch.backends.cudnn.benchmark = True
            
    def transcribe(self, audio_path: str, language: str = "auto") -> Dict:
        """
        Transcreve áudio com máxima precisão
        """
        try:
            # Configurações básicas compatíveis com todas as versões
            kwargs = {
                "verbose": False,
                "language": None if language == "auto" else language,
                "fp16": self.device == "cuda"
            }
            
            # Tenta adicionar word_timestamps se suportado
            try:
                # Teste rápido para ver se word_timestamps é suportado
                test_result = self.model.transcribe(audio_path, word_timestamps=True, verbose=False)
                kwargs["word_timestamps"] = True
            except:
                print("word_timestamps não suportado nesta versão do Whisper")
            
            # Transcrição principal
            result = self.model.transcribe(audio_path, **kwargs)
            
            # Processa segmentos para melhor formatação
            segments = self._process_segments(result.get("segments", []))
            
            return {
                "success": True,
                "text": result.get("text", ""),
                "segments": segments,
                "language": result.get("language", language),
                "duration": self._calculate_duration(segments)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_duration(self, segments: List[Dict]) -> float:
        """Calcula duração total baseada nos segmentos"""
        if not segments:
            return 0.0
        return max(segment.get("end", 0) for segment in segments)
    
    def _process_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Processa segmentos para melhor sincronização
        """
        processed = []
        
        for i, segment in enumerate(segments):
            # Remove espaços extras e ajusta timing
            text = segment.get("text", "").strip()
            if not text:
                continue
                
            processed_segment = {
                "id": segment.get("id", i),
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "text": text,
                "words": []
            }
            
            # Processa palavras individuais se disponível
            if "words" in segment and isinstance(segment["words"], list):
                for word in segment["words"]:
                    if isinstance(word, dict):
                        processed_segment["words"].append({
                            "word": word.get("word", ""),
                            "start": word.get("start", 0),
                            "end": word.get("end", 0),
                            "probability": word.get("probability", 1.0)
                        })
            
            processed.append(processed_segment)
        
        return processed