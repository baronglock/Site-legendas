# backend/services/subtitle_generator.py
from typing import List, Dict, Tuple
from pathlib import Path
import json
from datetime import timedelta
import tempfile
import os
from config import Config
from utils.r2_storage import R2Storage

class SubtitleGenerator:
    def __init__(self):
        self.r2_storage = R2Storage()
        self.temp_dir = tempfile.gettempdir()
        
    def generate_subtitles(self, segments: List[Dict], job_id: str, user_id: str,
                          max_line_width: int = 42, 
                          max_line_count: int = 2) -> Dict[str, str]:
        """
        Gera arquivos de legenda e faz upload para R2
        """
        print(f"\n=== GERANDO LEGENDAS ===")
        print(f"Job ID: {job_id}")
        print(f"Total de segmentos: {len(segments)}")
        
        # Otimiza quebras de linha
        optimized_segments = self._optimize_line_breaks(
            segments, max_line_width, max_line_count
        )
        
        # Gera arquivos temporários
        temp_files = {
            'srt': Path(self.temp_dir) / f"{job_id}.srt",
            'vtt': Path(self.temp_dir) / f"{job_id}.vtt",
            'json': Path(self.temp_dir) / f"{job_id}.json"
        }
        
        # Gera diferentes formatos
        self._generate_srt(optimized_segments, temp_files['srt'])
        self._generate_vtt(optimized_segments, temp_files['vtt'])
        self._save_json(optimized_segments, temp_files['json'])
        
        # Upload para R2
        r2_keys = {}
        r2_urls = {}
        
        try:
            for format_type, file_path in temp_files.items():
                if file_path.exists():
                    result = self.r2_storage.upload_file(
                        str(file_path),
                        user_id,
                        f'subtitles/{format_type}'
                    )
                    
                    if result['success']:
                        r2_keys[format_type] = result['key']
                        r2_urls[format_type] = result['url']
                    else:
                        print(f"Erro no upload {format_type}: {result.get('error')}")
                    
                    # Limpa arquivo temporário
                    file_path.unlink(missing_ok=True)
            
            return {
                'success': True,
                'keys': r2_keys,
                'urls': r2_urls
            }
            
        except Exception as e:
            # Limpa arquivos em caso de erro
            for file_path in temp_files.values():
                file_path.unlink(missing_ok=True)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _optimize_line_breaks(self, segments: List[Dict], 
                             max_width: int, max_lines: int) -> List[Dict]:
        """
        Otimiza quebras de linha para melhor leitura
        """
        optimized = []
        
        for segment in segments:
            text = segment["text"]
            words = segment.get("words", [])
            
            # Preserva informação de tradução se existir
            base_segment = {
                "id": len(optimized) + 1,
                "text": text
            }
            
            # Copia campos extras importantes
            if "original_text" in segment:
                base_segment["original_text"] = segment["original_text"]
            
            # Se tem informação de palavras, usa para melhor timing
            if words:
                lines = self._split_with_word_timing(words, max_width, max_lines)
                for i, line_data in enumerate(lines):
                    new_segment = base_segment.copy()
                    new_segment.update({
                        "id": len(optimized) + 1,
                        "start": line_data["start"],
                        "end": line_data["end"],
                        "text": line_data["text"]
                    })
                    optimized.append(new_segment)
            else:
                # Fallback para divisão simples
                lines = self._split_text(text, max_width, max_lines)
                duration = segment["end"] - segment["start"]
                time_per_line = duration / len(lines)
                
                for i, line in enumerate(lines):
                    new_segment = base_segment.copy()
                    new_segment.update({
                        "id": len(optimized) + 1,
                        "start": segment["start"] + (i * time_per_line),
                        "end": segment["start"] + ((i + 1) * time_per_line),
                        "text": line
                    })
                    optimized.append(new_segment)
        
        return optimized
    
    def _split_with_word_timing(self, words: List[Dict], 
                               max_width: int, max_lines: int) -> List[Dict]:
        """
        Divide texto usando timing de palavras
        """
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_text = word["word"].strip()
            word_length = len(word_text)
            
            # Verifica se precisa quebrar linha
            if current_length + word_length + 1 > max_width and current_line:
                # Cria linha com timing correto
                lines.append({
                    "text": " ".join([w["word"].strip() for w in current_line]),
                    "start": current_line[0]["start"],
                    "end": current_line[-1]["end"]
                })
                current_line = []
                current_length = 0
            
            current_line.append(word)
            current_length += word_length + 1
        
        # Adiciona última linha
        if current_line:
            lines.append({
                "text": " ".join([w["word"].strip() for w in current_line]),
                "start": current_line[0]["start"],
                "end": current_line[-1]["end"]
            })
        
        return lines
    
    def _split_text(self, text: str, max_width: int, max_lines: int) -> List[str]:
        """
        Divisão simples de texto
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_width and current_line:
                lines.append(" ".join(current_line))
                current_line = []
                current_length = 0
            
            current_line.append(word)
            current_length += len(word) + 1
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines
    
    def _generate_srt(self, segments: List[Dict], output_path: Path) -> Path:
        """
        Gera arquivo SRT
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._format_time_srt(segment["start"])
                end_time = self._format_time_srt(segment["end"])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        
        return output_path
    
    def _generate_vtt(self, segments: List[Dict], output_path: Path) -> Path:
        """
        Gera arquivo WebVTT
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            
            for segment in segments:
                start_time = self._format_time_vtt(segment["start"])
                end_time = self._format_time_vtt(segment["end"])
                
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        
        return output_path
    
    def _save_json(self, segments: List[Dict], output_path: Path) -> Path:
        """
        Salva transcrição em JSON
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def _format_time_srt(self, seconds: float) -> str:
        """Formata tempo para SRT (00:00:00,000)"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")
    
    def _format_time_vtt(self, seconds: float) -> str:
        """Formata tempo para WebVTT (00:00:00.000)"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"