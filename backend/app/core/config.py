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

    # The RuneScape Wiki APIs require a descriptive User-Agent
    USER_AGENT: str = os.getenv("USER_AGENT", "geFlipper - OSRS item price tracker ")
    # Set to "0" to run the API without the background collectors
    ENABLE_COLLECTORS: bool = os.getenv("ENABLE_COLLECTORS", "1") != "0"

settings = Settings()
