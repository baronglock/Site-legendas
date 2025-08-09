# backend/services/transcription.py
import torch
from pathlib import Path
from typing import Dict, List, Optional, BinaryIO
import json
import tempfile
import os
from config import Config
import warnings
warnings.filterwarnings("ignore")

# Import do faster-whisper (mais eficiente que openai-whisper)
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("Erro ao importar faster-whisper. Instale com: pip install faster-whisper")
    raise

class WhisperTranscriber:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or Config.WHISPER_MODEL_FREE
        self.device = Config.WHISPER_DEVICE
        self.compute_type = Config.WHISPER_COMPUTE_TYPE
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Carrega o modelo Whisper com otimizações"""
        print(f"Carregando modelo Whisper {self.model_name}...")
        
        # Verifica disponibilidade de CUDA
        if self.device == "cuda" and not torch.cuda.is_available():
            self.device = "cpu"
            self.compute_type = "int8"  # CPU usa int8
            print("CUDA não disponível, usando CPU")
        
        try:
            # Faster-whisper é mais eficiente
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=os.getenv('WHISPER_MODEL_PATH', None)
            )
            print(f"Modelo {self.model_name} carregado com sucesso!")
        except Exception as e:
            print(f"Erro ao carregar modelo {self.model_name}: {e}")
            # Fallback para modelo menor
            if self.model_name != "base":
                print("Tentando modelo 'base'...")
                self.model_name = "base"
                self.model = WhisperModel("base", device=self.device, compute_type="int8")
    
    def transcribe_from_r2(self, audio_url: str, language: str = "auto") -> Dict:
        """
        Transcreve áudio direto do R2
        """
        # Download temporário do R2
        import requests
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            try:
                # Download do arquivo
                response = requests.get(audio_url, stream=True)
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                
                tmp_file.flush()
                audio_path = tmp_file.name
                
                # Transcreve
                result = self.transcribe(audio_path, language)
                
                return result
                
            finally:
                # Limpa arquivo temporário
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)
    
    def transcribe(self, audio_path: str, language: str = "auto") -> Dict:
        """
        Transcreve áudio com máxima precisão usando faster-whisper
        """
        try:
            # Configurações para faster-whisper
            kwargs = {
                "language": None if language == "auto" else language,
                "task": "transcribe",
                "beam_size": 5,
                "best_of": 5,
                "patience": 1,
                "length_penalty": 1,
                "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                "compression_ratio_threshold": 2.4,
                "log_prob_threshold": -1.0,
                "no_speech_threshold": 0.6,
                "condition_on_previous_text": True,
                "word_timestamps": True,  # Importante para sincronização
                "prepend_punctuations": "\"'¿([{-",
                "append_punctuations": "\"'.。,，!！?？:：、",
            }
            
            # Transcrição
            segments, info = self.model.transcribe(audio_path, **kwargs)
            
            # Processa segmentos
            processed_segments = []
            for i, segment in enumerate(segments):
                processed_segment = {
                    "id": i,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "words": []
                }
                
                # Processa palavras se disponível
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        processed_segment["words"].append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        })
                
                processed_segments.append(processed_segment)
            
            # Detecta idioma
            detected_language = info.language if hasattr(info, 'language') else language
            
            return {
                "success": True,
                "text": " ".join([s["text"] for s in processed_segments]),
                "segments": processed_segments,
                "language": detected_language,
                "duration": info.duration if hasattr(info, 'duration') else self._calculate_duration(processed_segments)
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