from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from enum import Enum

class WhisperModel(str, Enum):
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"

class Language(str, Enum):
    AUTO = "auto"
    PT = "pt"
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    JA = "ja"
    KO = "ko"
    ZH = "zh"

class SubtitleRequest(BaseModel):
    vimeo_url: HttpUrl = Field(..., description="URL do vídeo no Vimeo")
    language: Language = Field(Language.AUTO, description="Idioma para transcrição")
    translate_to_pt: bool = Field(True, description="Traduzir legendas para português")
    model: Optional[WhisperModel] = Field(None, description="Modelo Whisper (usa config padrão se não especificado)")
    word_timestamps: bool = Field(True, description="Incluir timestamps por palavra")
    max_line_width: int = Field(42, description="Largura máxima da linha em caracteres")
    max_line_count: int = Field(2, description="Número máximo de linhas por legenda")

class SubtitleResponse(BaseModel):
    success: bool
    video_id: str
    srt_path: Optional[str] = None
    srt_translated_path: Optional[str] = None
    vtt_path: Optional[str] = None
    vtt_translated_path: Optional[str] = None
    json_path: Optional[str] = None
    error: Optional[str] = None
    processing_time: float
    detected_language: Optional[str] = None
    was_translated: bool = False

class TranscriptionSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: Optional[List[dict]] = None