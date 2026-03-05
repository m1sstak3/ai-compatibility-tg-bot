import uuid
from sqlalchemy import Column, Integer, String, BigInteger
from sqlalchemy.dialects.postgresql import UUID as PGUUID # For better postgres support later if needed, fallback to generic UUID
from sqlalchemy.types import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    gender = Column(String, nullable=True) 
    is_distance = Column(String, nullable=True) # "yes" или "no"

class GameSession(Base):
    """
    Optional DB model if you want to persist sessions across restarts.
    Currently, we will move state management into memory or redis-backed FSM, 
    but we keep the schema for history.
    """
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    p1_id = Column(BigInteger)
    p2_id = Column(BigInteger, nullable=True)
    status = Column(String, default="WAITING")
