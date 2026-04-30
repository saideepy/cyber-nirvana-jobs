import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    Float, DateTime, Text, ForeignKey
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


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_admin      = Column(Boolean, default=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token         = Column(String, unique=True, nullable=False, index=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_seen     = Column(DateTime, default=datetime.utcnow)
    logged_out_at = Column(DateTime, nullable=True)
    is_active     = Column(Boolean, default=True)


class JobApplication(Base):
    __tablename__ = "job_applications"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id       = Column(Integer, nullable=False)
    job_title    = Column(String, default="")
    job_category = Column(String, default="")
    job_url      = Column(String, default="")
    applied_at   = Column(DateTime, default=datetime.utcnow)
    is_active    = Column(Boolean, default=True)


def create_tables():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
