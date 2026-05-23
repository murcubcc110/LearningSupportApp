# app/infrastructure/database/habit_tracker_db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# データベースのディレクトリ作成とURL定義
os.makedirs("./resource/db", exist_ok=True)
DATABASE_URL = "sqlite:///./resource/db/habit_tracker.db"

# SQLAlchemy エンジンの作成
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30}
)

# セッション設定
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基底クラス
Base = declarative_base()

def get_db():
    """習慣トラッカー用セッション管理依存性注入関数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
