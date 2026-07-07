from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "AI Berkshire"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "ai-berkshire-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "sqlite:///./ai_berkshire.db"
    
    # AI API Keys
    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    AI_PROVIDER: str = "openai"  # openai | deepseek
    AI_MODEL: str = "gpt-4o-mini"
    
    # Data Sources
    TUSHARE_TOKEN: str = ""
    AKSHARE_ENABLED: bool = True
    USE_REAL_DATA: bool = True
    NETWORK_TIMEOUT: int = 3
    ENABLE_AKSHARE_BREADTH: bool = False
    AUTO_SEED_DB: bool = False
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        value = self.CORS_ORIGINS.strip()
        if value == "*":
            return ["*"]
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
