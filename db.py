from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from environs import Env

env = Env()  # Создаем экземпляр класса Env
env.read_env()  # Методом read_env() читаем файл .env и загружаем из него переменные в окружение

DATABASE_URL=f"postgresql+asyncpg://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}@{env('POSTGRES_HOST')}:5432/{env('POSTGRES_DB')}"

engine = create_async_engine(DATABASE_URL)

async def init_db():
    from sqlmodel import SQLModel
    import asyncio
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

def get_session():
    from sqlmodel.ext.asyncio.session import AsyncSession
    return AsyncSession(engine)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    email: str
    phone_number: str
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    password_hash: str


app = FastAPI()

# Инициализация базы
@app.on_event("startup")
async def startup_event():
    await init_db()

