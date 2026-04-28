import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    Float, DateTime, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

_default_data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DATA_DIR = os.environ.get("DATA_DIR", _default_data)
DB_PATH = os.path.join(DATA_DIR, "jobs.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id             = Column(Integer, primary_key=True, index=True)
    url            = Column(String, unique=True, index=True, nullable=False)
    title          = Column(String, default="")
    company        = Column(String, default="")
    location       = Column(String, default="")
    salary         = Column(String, default="")
    posted_date    = Column(String, default="")
    scraped_at     = Column(DateTime, default=datetime.utcnow)
    source         = Column(String, default="")
    role_category  = Column(String, default="")
    description    = Column(Text, default="")
    is_c2c         = Column(Boolean, default=False)
    is_vendor      = Column(Boolean, default=False)
    semantic_score = Column(Float, default=0.0)
    status         = Column(String, default="new")


def create_tables():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
