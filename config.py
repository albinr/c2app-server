# config.py
import secrets
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class Config:
    SECRET_KEY = secrets.token_hex(16)
    DATABASE_URL = "sqlite+aiosqlite:///sqlite.db"

    DEBUG = True
    TESTING = True 

    async_engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
