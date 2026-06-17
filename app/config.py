from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./puppet_management.db"
    SECRET_KEY: str = "puppet-management-secret-key-for-jwt-token"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    API_PORT: int = 8114

    class Config:
        env_file = ".env"


settings = Settings()
