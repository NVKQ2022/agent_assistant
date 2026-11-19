from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Azure OpenAI / OpenAI Settings
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-5.6-luna"

    # Backend Service URL (for tools to interact with)
    backend_url: str = "http://localhost:8002"

    # Agent Service Settings
    host: str = "0.0.0.0"
    port: int = 8001
    app_name: str = "Agent Assistant Service"


settings = Settings()
