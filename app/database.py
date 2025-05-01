from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import psycopg2
import os

# Load environment variables from the .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql+psycopg2://")

engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_database_if_not_exists():
    engine = create_engine(DATABASE_URL)
    connection = engine.raw_connection()
    database_name = DATABASE_URL.split('/')[-1]
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        cursor.execute(f'CREATE DATABASE {database_name}')
    except OperationalError:
        pass
    finally:
        cursor.close()

