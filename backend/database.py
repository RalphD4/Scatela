import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

# Load environment variables from .env when running outside Docker Compose
load_dotenv()


def build_database_url() -> str:
    """Build the SQLAlchemy database URI from environment variables."""
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "")

    return (
        f"postgresql+psycopg2://"
        f"{quote_plus(user)}:{quote_plus(password)}@"
        f"{host}:{port}/{dbname}"
    )


DATABASE_URL = build_database_url()

# Shared SQLAlchemy instance
db = SQLAlchemy()
