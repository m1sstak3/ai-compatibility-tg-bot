import logging
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.core.config import DB_URL
from src.database.models import Base, User

logger = logging.getLogger(__name__)

engine = create_async_engine(DB_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    """Initializes the database schema."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database models initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing DB schema: {e}")

async def get_user_data(tg_id: int) -> Optional[Dict[str, str]]:
    """Fetch user profile settings."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            return {
                "gender": user.gender, 
                "is_distance": user.is_distance
            }
        return None

async def save_user_gender(tg_id: int, gender: str, username: Optional[str] = None) -> None:
    """Save or update user's gender."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(tg_id=tg_id, username=username, gender=gender)
            session.add(user)
        else:
            user.gender = gender
        await session.commit()

async def save_user_residency(tg_id: int, is_distance: str) -> None:
    """Save or update user's residency status ('yes' or 'no')."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_distance = is_distance
            await session.commit()
