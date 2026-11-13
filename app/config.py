from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://alllove_user:alllove_password@localhost:5433/alllove_db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = str(BASE_DIR / "storage" / "documents")
    BACKUP_DIR: str = str(BASE_DIR / "storage" / "backups")
    BACKUP_KEEP_DAYS: int = 7
    BACKUP_HOUR: int = 3
    BACKUP_SCHEDULE_ENABLED: bool = True
    SSL_DIR: str = str(BASE_DIR / "deploy" / "certs")

    class Config:
        env_file = ".env"


settings = Settings()
