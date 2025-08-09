from urllib.parse import urlparse
import re
from typing import Optional, Tuple
import magic
from pathlib import Path

class Validators:
    # Padrões de URL para diferentes plataformas
    URL_PATTERNS = {
        'youtube': [
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'https?://youtu\.be/[\w-]+',
            r'https?://m\.youtube\.com/watch\?v=[\w-]+'
        ],
        'vimeo': [
            r'https?://(?:www\.)?vimeo\.com/\d+',
            r'https?://player\.vimeo\.com/video/\d+',
            r'https?://vimeo\.com/channels/[\w-]+/\d+',
            r'https?://vimeo\.com/groups/[\w-]+/videos/\d+'
        ],
        'twitter': [
            r'https?://(?:www\.)?twitter\.com/\w+/status/\d+',
            r'https?://(?:www\.)?x\.com/\w+/status/\d+'
        ],
        'tiktok': [
            r'https?://(?:www\.)?tiktok\.com/@[\w.]+/video/\d+',
            r'https?://vm\.tiktok\.com/[\w-]+'
        ]
    }
    
    @staticmethod
    def is_valid_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Valida URL e retorna plataforma
        """
        for platform, patterns in Validators.URL_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, url):
                    return True, platform
        
        # Verifica se é uma URL válida genérica
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                return True, 'generic'
        except:
            pass
        
        return False, None
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Valida formato de email
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_file_upload(file_path: str, max_size_mb: int) -> Tuple[bool, Optional[str]]:
        """
        Valida arquivo enviado
        """
        from config import Config
        
        path = Path(file_path)
        
        # Verifica se existe
        if not path.exists():
            return False, "Arquivo não encontrado"
        
        # Verifica tamanho
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"Arquivo muito grande. Máximo: {max_size_mb}MB"
        
        # Verifica tipo MIME
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(path))
            
            allowed_mimes = [
                'video/mp4', 'video/quicktime', 'video/x-msvideo',
                'video/x-matroska', 'video/webm',
                'audio/mpeg', 'audio/wav', 'audio/x-wav',
                'audio/mp4', 'audio/aac'
            ]
            
            if file_type not in allowed_mimes:
                return False, f"Tipo de arquivo não suportado: {file_type}"
        except:
            # Fallback para extensão
            ext = path.suffix.lower()
            allowed_exts = Config.ALLOWED_VIDEO_EXTENSIONS + Config.ALLOWED_AUDIO_EXTENSIONS
            
            if ext not in allowed_exts:
                return False, f"Extensão não suportada: {ext}"
        
        return True, None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Remove caracteres perigosos do nome do arquivo
        """
        # Remove path traversal
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Mantém apenas caracteres seguros
        safe_chars = re.sub(r'[^\w\s.-]', '', filename)
        
        # Limita tamanho
        if len(safe_chars) > 255:
            name, ext = safe_chars.rsplit('.', 1) if '.' in safe_chars else (safe_chars, '')
            safe_chars = name[:250] + '.' + ext if ext else name[:255]
        
        return safe_chars
    
    @staticmethod
    def estimate_duration_from_size(file_size_bytes: int, file_type: str) -> float:
        """
        Estima duração baseada no tamanho do arquivo
        """
        # Bitrates médios aproximados (em kbps)
        avg_bitrates = {
            'video': 5000,  # 5 Mbps para vídeo
            'audio': 192    # 192 kbps para áudio
        }
        
        bitrate = avg_bitrates.get(file_type, 1000)
        
        # Converte para segundos
        duration_seconds = (file_size_bytes * 8) / (bitrate * 1000)
        
        return duration_seconds
    
    @staticmethod
    def validate_language_pair(source: str, target: str) -> Tuple[bool, Optional[str]]:
        """
        Valida par de idiomas para tradução
        """
        # Idiomas suportados
        supported_languages = [
            'pt', 'en', 'es', 'fr', 'de', 'it', 
            'ja', 'ko', 'zh', 'ru', 'ar', 'hi'
        ]
        
        if source not in supported_languages:
            return False, f"Idioma de origem não suportado: {source}"
        
        if target not in supported_languages:
            return False, f"Idioma de destino não suportado: {target}"
        
        if source == target:
            return False, "Idiomas de origem e destino são iguais"
        
        return True, None