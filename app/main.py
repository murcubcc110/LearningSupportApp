# app/main.py
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


from app.core.config import settings

# データベース設定・モデルのインポート
from app.infrastructure.database.habit_tracker_db import Base as HTBase, engine as HTEngine, SessionLocal as HTSessionLocal
from app.infrastructure.database.models.habit_tracker import TrackerDB, DailyRecordDB, CharacterDB

# リポジトリ・ユースケース・ルーター
from app.infrastructure.repositories.sqlalchemy_tracker_repository import SQLAlchemyTrackerRepository
from app.infrastructure.ai.llm_feedback_service import LLMFeedbackService
from app.usecases.tracker.tracker_usecase import TrackerUseCase
from app.api.endpoints import habit_tracker

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
)

# データベース初期化・マイグレーション・クリーンアップ
def init_databases():
    # テーブル自動生成
    HTBase.metadata.create_all(bind=HTEngine)
    
    # 既存DBテーブルへカラム user_message を動的に追加（SQLiteマイグレーション）
    try:
        import sqlalchemy
        inspector = sqlalchemy.inspect(HTEngine)
        columns = [col['name'] for col in inspector.get_columns('daily_records')]
        if 'user_message' not in columns:
            with HTEngine.connect() as conn:
                conn.execute(sqlalchemy.text("ALTER TABLE daily_records ADD COLUMN user_message TEXT"))
                conn.commit()
            logger.info("Database migration: Added user_message column to daily_records table.")
    except Exception as migration_err:
        logger.error(f"Error during SQLite migration: {migration_err}")
    
    # キャラクター初期データシード
    db = HTSessionLocal()
    try:
        from app.core.prompts import SYSTEM_PROMPTS, COMMON_JSON_FORMAT
        
        # ai_ch_01 prompt excluding COMMON_JSON_FORMAT
        ogami_prompt = SYSTEM_PROMPTS["ai_ch_01"].replace(COMMON_JSON_FORMAT, "").strip()
        # ai_ch_02 prompt excluding COMMON_JSON_FORMAT
        mio_prompt = SYSTEM_PROMPTS["ai_ch_02"].replace(COMMON_JSON_FORMAT, "").strip()
        
        ogami = db.query(CharacterDB).filter(CharacterDB.id == "ai_ch_01").first()
        if not ogami:
            ogami = CharacterDB(
                id="ai_ch_01",
                name="巌狼",
                avatar_url="/static/genro.png",
                system_prompt=ogami_prompt
            )
            db.add(ogami)
            logger.info("Database seeded: ai_ch_01 added.")
        else:
            ogami.system_prompt = ogami_prompt
            db.add(ogami)

        mio = db.query(CharacterDB).filter(CharacterDB.id == "ai_ch_02").first()
        if not mio:
            mio = CharacterDB(
                id="ai_ch_02",
                name="こはる",
                avatar_url="/static/koharu.png",
                system_prompt=mio_prompt
            )
            db.add(mio)
            logger.info("Database seeded: ai_ch_02 added.")
        else:
            mio.system_prompt = mio_prompt
            db.add(mio)
            
        db.commit()
    except Exception as e:
        logger.error(f"Error seeding characters: {e}")
        db.rollback()
    finally:
        db.close()

# アプリ起動時処理
@app.on_event("startup")
def startup_event():
    init_databases()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルの設定
app.mount("/static", StaticFiles(directory="static"), name="static")

# ルーターの登録
app.include_router(habit_tracker.router, tags=["Habit Tracker"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
