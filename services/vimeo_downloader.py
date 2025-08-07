import yt_dlp
import os
from pathlib import Path
from typing import Optional, Dict
import hashlib
import subprocess
import json
from config import Config

class VimeoDownloader:
    def __init__(self):
        self.output_dir = Config.VIDEO_DIR
        
    def download(self, vimeo_url: str, quality: str = "best") -> Dict[str, any]:
        """
        Baixa vídeo do Vimeo com múltiplas estratégias
        """
        # Gera ID único baseado na URL
        video_id = hashlib.md5(vimeo_url.encode()).hexdigest()[:12]
        output_path = self.output_dir / f"{video_id}.mp4"
        
        # Se já existe, retorna o caminho
        if output_path.exists():
            print(f"Vídeo já existe em cache: {output_path}")
            return {
                "success": True,
                "video_id": video_id,
                "path": str(output_path),
                "cached": True
            }
        
        print(f"Iniciando download de: {vimeo_url}")
        
        # Tenta diferentes métodos
        methods = [
            ("Método 1: YT-DLP Básico", self._download_method_1),
            ("Método 2: YT-DLP com cookies", self._download_method_2),
            ("Método 3: YT-DLP linha de comando", self._download_method_3),
            ("Método 4: Gallery-dl", self._download_method_4),
        ]
        
        for method_name, method_func in methods:
            print(f"\nTentando {method_name}...")
            result = method_func(vimeo_url, output_path, video_id)
            if result["success"]:
                print(f"✓ Sucesso com {method_name}")
                return result
            else:
                print(f"✗ Falhou: {result.get('error', 'Erro desconhecido')}")
        
        # Se todos falharam
        return {
            "success": False,
            "error": "Não foi possível baixar o vídeo. Possíveis causas:\n" +
                    "1. Vídeo privado ou protegido\n" +
                    "2. Requer login/senha\n" +
                    "3. Bloqueio regional\n" +
                    "Tente com um vídeo público ou forneça cookies de autenticação.",
            "video_id": video_id
        }
    
    def _download_method_1(self, url: str, output_path: Path, video_id: str) -> Dict:
        """Método 1: YT-DLP configuração básica"""
        ydl_opts = {
            'outtmpl': str(output_path),
            'format': 'best[ext=mp4]/best',
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            # Headers para parecer um navegador real
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://vimeo.com/'
            },
            # Tenta contornar proteções
            'age_limit': None,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if output_path.exists():
                    return {
                        "success": True,
                        "video_id": video_id,
                        "path": str(output_path),
                        "title": info.get('title', 'Unknown'),
                        "duration": info.get('duration', 0),
                        "cached": False
                    }
                
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
        
        return {"success": False, "error": "Download falhou"}
    
    def _download_method_2(self, url: str, output_path: Path, video_id: str) -> Dict:
        """Método 2: YT-DLP com cookies (se disponível)"""
        cookies_file = Path("cookies.txt")
        
        ydl_opts = {
            'outtmpl': str(output_path),
            'format': 'best',
            'quiet': True,
        }
        
        # Se tiver arquivo de cookies, usa
        if cookies_file.exists():
            ydl_opts['cookiefile'] = str(cookies_file)
            print("Usando cookies.txt encontrado")
        else:
            print("Sem cookies.txt - criando arquivo de exemplo")
            self._create_cookies_example()
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                if output_path.exists():
                    return {
                        "success": True,
                        "video_id": video_id,
                        "path": str(output_path),
                        "cached": False
                    }
                    
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
            
        return {"success": False, "error": "Download falhou"}
    
    def _download_method_3(self, url: str, output_path: Path, video_id: str) -> Dict:
        """Método 3: YT-DLP via linha de comando"""
        try:
            # Comando básico
            cmd = [
                'yt-dlp',
                '-f', 'best',
                '-o', str(output_path),
                '--no-check-certificate',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                url
            ]
            
            # Executa
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if output_path.exists():
                return {
                    "success": True,
                    "video_id": video_id,
                    "path": str(output_path),
                    "cached": False
                }
            
            return {"success": False, "error": result.stderr[:200] if result.stderr else "Falhou"}
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout - download muito demorado"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
    
    def _download_method_4(self, url: str, output_path: Path, video_id: str) -> Dict:
        """Método 4: Gallery-dl como alternativa"""
        try:
            # Verifica se gallery-dl está instalado
            subprocess.run(['gallery-dl', '--version'], capture_output=True)
            
            cmd = [
                'gallery-dl',
                '--dest', str(self.output_dir),
                '--filename', f"{video_id}.mp4",
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if output_path.exists():
                return {
                    "success": True,
                    "video_id": video_id,
                    "path": str(output_path),
                    "cached": False
                }
                
        except FileNotFoundError:
            return {"success": False, "error": "gallery-dl não instalado"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
            
        return {"success": False, "error": "Download falhou"}
    
    def _create_cookies_example(self):
        """Cria arquivo de exemplo para cookies"""
        example = """# Netscape HTTP Cookie File
# This is a generated file!  Do not edit.
# Para usar cookies do Vimeo:
# 1. Instale a extensão "Get cookies.txt" no Chrome/Firefox
# 2. Faça login no Vimeo
# 3. Vá para vimeo.com
# 4. Clique na extensão e exporte os cookies
# 5. Substitua este arquivo pelo arquivo exportado

# Exemplo de formato:
# .vimeo.com	TRUE	/	TRUE	1234567890	cookie_name	cookie_value
"""
        with open("cookies_example.txt", "w") as f:
            f.write(example)
        print("Criado cookies_example.txt - veja as instruções no arquivo")
    
    def get_video_info(self, url: str) -> Dict:
        """Obtém informações do vídeo sem baixar"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "success": True,
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 0),
                    "uploader": info.get('uploader', 'Unknown'),
                    "is_private": info.get('is_private', False),
                    "formats_available": len(info.get('formats', []))
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)[:200]
            }

# Função auxiliar para testar URLs
def test_vimeo_url(url: str):
    """Função para testar se uma URL do Vimeo é acessível"""
    downloader = VimeoDownloader()
    info = downloader.get_video_info(url)
    
    if info["success"]:
        print(f"✓ Vídeo acessível: {info['title']}")
        print(f"  Duração: {info['duration']}s")
        print(f"  Uploader: {info['uploader']}")
        print(f"  Privado: {info['is_private']}")
    else:
        print(f"✗ Erro ao acessar: {info['error']}")
    
    return info

# URLs de teste conhecidas que funcionam
VIMEO_TEST_URLS = [
    "https://vimeo.com/70591644",  # Big Buck Bunny
    "https://vimeo.com/153339497", # Sample video
    "https://vimeo.com/22439234",  # The Mountain
]