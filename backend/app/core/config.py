# configuration for sqlalchemy database connection
# postgresql+asyncpg://<username>:<password>@<host>/<database_name>
import urllib.parse

class Settings:
    DB_USER: str = "root"
    DB_PASS: str = urllib.parse.quote_plus("TESTED12#!!@#!22")
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "geflipper"
    DATABASE_URL: str = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"