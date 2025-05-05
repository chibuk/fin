import os
from sqlmodel import create_engine, SQLModel
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL, echo=True)

async def init_db():
    from sqlmodel import SQLModel
    import asyncio
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

def get_session():
    from sqlmodel.ext.asyncio.session import AsyncSession
    return AsyncSession(engine)
