from typing import List, Dict, Tuple
from pathlib import Path
import json
from datetime import timedelta
from config import Config

class SubtitleGenerator:
    def __init__(self):
        self.output_dir = Config.SUBTITLE_DIR
        
    def generate_subtitles(self, segments: List[Dict], video_id: str, 
                          max_line_width: int = 42, 
                          max_line_count: int = 2) -> Dict[str, str]:
        """
        Gera arquivos de legenda em múltiplos formatos
        """

        print(f"\n=== DEBUG SUBTITLE GENERATOR ===")
        print(f"Gerando legendas para: {video_id}")
        print(f"Total de segmentos: {len(segments)}")
        if segments:
            print(f"Primeiro segmento: {segments[0].get('text', 'SEM TEXTO')[:50]}...")
            print(f"Campos disponíveis: {list(segments[0].keys())}")
        print("================================\n")
        
        # Otimiza quebras de linha
        optimized_segments = self._optimize_line_breaks(
            segments, max_line_width, max_line_count
        )
        
        # Gera diferentes formatos
        srt_path = self._generate_srt(optimized_segments, video_id)
        vtt_path = self._generate_vtt(optimized_segments, video_id)
        json_path = self._save_json(optimized_segments, video_id)
        
        return {
            "srt": str(srt_path),
            "vtt": str(vtt_path),
            "json": str(json_path)
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
            
            # Se tem informação de palavras, usa para melhor timing
            if words:
                lines = self._split_with_word_timing(words, max_width, max_lines)
                for i, line_data in enumerate(lines):
                    optimized.append({
                        "id": len(optimized) + 1,
                        "start": line_data["start"],
                        "end": line_data["end"],
                        "text": line_data["text"]
                    })
            else:
                # Fallback para divisão simples
                lines = self._split_text(text, max_width, max_lines)
                duration = segment["end"] - segment["start"]
                time_per_line = duration / len(lines)
                
                for i, line in enumerate(lines):
                    optimized.append({
                        "id": len(optimized) + 1,
                        "start": segment["start"] + (i * time_per_line),
                        "end": segment["start"] + ((i + 1) * time_per_line),
                        "text": line
                    })
        
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
    
    def _generate_srt(self, segments: List[Dict], video_id: str) -> Path:
        """
        Gera arquivo SRT
        """
        srt_path = self.output_dir / f"{video_id}.srt"
        
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._format_time_srt(segment["start"])
                end_time = self._format_time_srt(segment["end"])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        
        return srt_path
    
    def _generate_vtt(self, segments: List[Dict], video_id: str) -> Path:
        """
        Gera arquivo WebVTT
        """
        vtt_path = self.output_dir / f"{video_id}.vtt"
        
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            
            for segment in segments:
                start_time = self._format_time_vtt(segment["start"])
                end_time = self._format_time_vtt(segment["end"])
                
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        
        return vtt_path
    
    def _save_json(self, segments: List[Dict], video_id: str) -> Path:
        """
        Salva transcrição em JSON
        """
        json_path = self.output_dir / f"{video_id}.json"
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        
        return json_path
    
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