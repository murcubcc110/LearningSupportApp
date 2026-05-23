from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json

class Settings(BaseSettings):
    # LLM Settings
    LLM_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    LLM_MODEL_NAME: str = "gemini-1.5-flash"
    GEMINI_API_KEY: str = ""

    # App Settings
    APP_TITLE: str = "巌狼の愛の鞭 API"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
