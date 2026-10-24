import os

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine


#get env variables
load_dotenv()

#database url  postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"postgres:5432/"
    f"{os.getenv('POSTGRES_DB')}"
)



#db instance
db = SQLAlchemy()
