# configuration for sqlalchemy database connection
import os
import urllib.parse

class Settings:
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASS: str = urllib.parse.quote_plus(os.getenv("DB_PASS", ""))
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "geflipper")
    DATABASE_URL: str = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

settings = Settings()
