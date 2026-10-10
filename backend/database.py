import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

#get env variables
load_dotenv()

#database
DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"postgres:5432/"
    f"{os.getenv('POSTGRES_USER')}"
)

engine = create_engine(DATABASE_URL)