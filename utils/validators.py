from urllib.parse import urlparse
import re

class Validators:
    @staticmethod
    def is_valid_vimeo_url(url: str) -> bool:
        """Valida URL do Vimeo"""
        patterns = [
            r'https?://(?:www\.)?vimeo\.com/\d+',
            r'https?://player\.vimeo\.com/video/\d+',
            r'https?://vimeo\.com/channels/[\w-]+/\d+',
            r'https?://vimeo\.com/groups/[\w-]+/videos/\d+'
        ]
        
        return any(re.match(pattern, url) for pattern in patterns)
    
    @staticmethod
    def extract_vimeo_id(url: str) -> str:
        """Extrai ID do vídeo Vimeo"""
        match = re.search(r'/(\d+)', url)
        return match.group(1) if match else None