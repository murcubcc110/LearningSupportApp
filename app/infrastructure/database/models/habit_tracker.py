# app/infrastructure/database/models/habit_tracker.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from app.infrastructure.database.habit_tracker_db import Base

class TrackerDB(Base):
    """
    SQLAlchemy ORM：習慣トラッカー設定モデル
    """
    __tablename__ = "trackers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False, index=True)
    period_days = Column(Integer, default=7, nullable=False)
    start_date = Column(Date, default=datetime.date.today, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    ai_comment = Column(String, default="新しいチャレンジが始まりました！最初の一歩を踏み出しましょう。", nullable=True)
    ai_status = Column(String, default="encourage", nullable=True)
    character = Column(String, default="ai_ch_01", nullable=False)

    records = relationship("DailyRecordDB", back_populates="tracker", cascade="all, delete-orphan", order_by="DailyRecordDB.day_number")


class DailyRecordDB(Base):
    """
    SQLAlchemy ORM：日々の達成状況記録モデル
    """
    __tablename__ = "daily_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracker_id = Column(Integer, ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False)
    day_number = Column(Integer, nullable=False)
    status = Column(String, default="pending", nullable=False)  # "pending", "achieved", "slacked"
    recorded_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)

    tracker = relationship("TrackerDB", back_populates="records")


class CharacterDB(Base):
    """
    SQLAlchemy ORM：AIキャラクター設定モデル
    """
    __tablename__ = "characters"

    id = Column(String, primary_key=True, index=True)  # "ai_ch_01", "ai_ch_02"
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=False)
    system_prompt = Column(String, nullable=False)

