from pathlib import Path
from typing import Optional, Literal, List
from pydantic import SecretStr, Field, validator
from pydantic_settings import BaseSettings

LLMProvider = Literal["openai", "anthropic", "qwen", "wenxin"]


class LLMConfig(BaseSettings):
    provider: LLMProvider = "qwen"
    model: str = "qwen-max"
    api_key: Optional[SecretStr] = None
    base_url: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.3
    timeout: int = 30

    @validator("temperature")
    def validate_temperature(cls, v):
        if not (0 <= v <= 2):
            raise ValueError("temperature must be between 0 and 2")
        return v

    @validator("max_tokens")
    def validate_max_tokens(cls, v):
        if v <= 0:
            raise ValueError("max_tokens must be positive")
        return v


class NewsCollectorConfig(BaseSettings):
    fetch_interval: int = 300
    timeout: int = 8
    retry_times: int = 2
    max_items_per_source: int = 20
    hard_timeout: int = 20
    enabled_sources: Optional[List[str]] = None
    deduplication_threshold: float = 0.85

    @validator("deduplication_threshold")
    def validate_threshold(cls, v):
        if not (0 <= v <= 1):
            raise ValueError("deduplication_threshold must be between 0 and 1")
        return v


class DatabaseConfig(BaseSettings):
    url: str = "sqlite:///./data/news_analyst.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class APIConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]
    rate_limit: str = "10/minute"
    daily_report_theme: str = "light"


class VisualizerConfig(BaseSettings):
    theme: str = "light"
    width: int = 1200
    height: int = 1600
    output_dir: Path = Path("./output/images")


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    dir: Path = Path("./logs")
    rotation: str = "10 MB"
    retention: str = "30 days"


class Settings(BaseSettings):
    llm: LLMConfig = LLMConfig()
    news: NewsCollectorConfig = NewsCollectorConfig()
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    visualizer: VisualizerConfig = VisualizerConfig()
    logging: LoggingConfig = LoggingConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        extra = "ignore"

    def get_llm_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        p = provider or self.llm.provider
        env_keys = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "qwen": "QWEN_API_KEY",
            "wenxin": "WENXIN_API_KEY",
        }
        import os

        key = os.getenv(env_keys.get(p))
        return key

    def get_wenxin_secret_key(self) -> Optional[str]:
        import os

        return os.getenv("WENXIN_SECRET_KEY")


settings = Settings()
