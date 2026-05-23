# app/infrastructure/database/models/learning_support.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
import datetime
from app.infrastructure.database.learning_support_db import Base

class UserStatsDB(Base):
    """
    SQLAlchemy ORM：ユーザー学習統計情報モデル
    """
    __tablename__ = "user_stats"
    user_id = Column(String, primary_key=True, index=True)
    consecutive_days = Column(Integer, default=0)
    last_practice_date = Column(DateTime, default=None)


class HistoryDB(Base):
    """
    SQLAlchemy ORM：おみくじ対話履歴情報モデル
    """
    __tablename__ = "conversation_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    character_id = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    user_message = Column(Text)
    followed_plan = Column(Boolean)
    consecutive_days = Column(Integer)
    fortune = Column(String)
    katsu = Column(Text)
    advice = Column(Text)
    next_action_advice = Column(Text)
