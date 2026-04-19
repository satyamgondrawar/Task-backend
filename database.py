from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./tasks.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # 🔥 important for SQLite
)
print("Database connected successfully!")

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()