from pydantic import BaseModel, HttpUrl, Field, EmailStr
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime

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
    RU = "ru"
    AR = "ar"
    HI = "hi"

class UserPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    COMPLETED = "completed"
    FAILED = "failed"

# Request/Response Models
class UserRegister(BaseModel):
    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    plan: UserPlan
    minutes_available: float