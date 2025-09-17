# db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

#load_dotenv()  # loads .env in same folder if present
#load_dotenv(dotenv_path='.env.example')
load_dotenv(dotenv_path='backend/.env')

#DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_health")
DATABASE_URL = os.getenv("DATABASE_URL","postgresql://ai_health_db_ukjx_user:zsydDs4BMcJX6bYVFj7v4iamTfvSuMlA@dpg-d30i7k0gjchc73esjaag-a.oregon-postgres.render.com/ai_health_db_ukjx" )
# Synchronous engine (simple for prototype)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
