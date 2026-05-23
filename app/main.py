# app/main.py
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import inspect, text

from app.core.config import settings

# データベース設定・モデルのインポート
from app.infrastructure.database.habit_tracker_db import Base as HTBase, engine as HTEngine, SessionLocal as HTSessionLocal
from app.infrastructure.database.models.habit_tracker import TrackerDB, DailyRecordDB, CharacterDB

from app.infrastructure.database.learning_support_db import Base as LSBase, engine as LSEngine, SessionLocal as LSSessionLocal
from app.infrastructure.database.models.learning_support import UserStatsDB, HistoryDB

# リポジトリ・ユースケース・ルーター
from app.infrastructure.repositories.sqlalchemy_user_stats_repository import SQLAlchemyUserStatsRepository
from app.infrastructure.ai.llm_feedback_service import LLMFeedbackService
from app.usecases.learning_support.learning_support_usecase import LearningSupportUseCase
from app.api.endpoints import habit_tracker, omikuji

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
    LSBase.metadata.create_all(bind=LSEngine)
    
    # 習慣トラッカーマイグレーション: trackersテーブルにcharacterカラムが存在しない場合は追加
    inspector = inspect(HTEngine)
    try:
        columns = [col['name'] for col in inspector.get_columns('trackers')]
        if 'character' not in columns:
            with HTEngine.connect() as conn:
                conn.execute(text("ALTER TABLE trackers ADD COLUMN character VARCHAR DEFAULT 'ogami'"))
                conn.commit()
            logger.info("Migration successful: added 'character' column to 'trackers'")
    except Exception as e:
        logger.error(f"Migration error: {e}")

    # キャラクター初期データシード
    db = HTSessionLocal()
    try:
        if db.query(CharacterDB).count() == 0:
            from app.core.prompts import SYSTEM_PROMPTS, COMMON_JSON_FORMAT
            
            # ogami prompt excluding COMMON_JSON_FORMAT
            ogami_prompt = SYSTEM_PROMPTS["ogami"].replace(COMMON_JSON_FORMAT, "").strip()
            # mio prompt excluding COMMON_JSON_FORMAT
            mio_prompt = SYSTEM_PROMPTS["mio"].replace(COMMON_JSON_FORMAT, "").strip()
            
            ogami = CharacterDB(
                id="ogami",
                name="大神様",
                avatar_url="/static/ogami_sama.png",
                system_prompt=ogami_prompt
            )
            mio = CharacterDB(
                id="mio",
                name="ミオ",
                avatar_url="/static/mio.png",
                system_prompt=mio_prompt
            )
            db.add(ogami)
            db.add(mio)
            db.commit()
            logger.info("Database seeded: default characters added.")
    except Exception as e:
        logger.error(f"Error seeding characters: {e}")
    finally:
        db.close()

def run_startup_cleanup():
    db = LSSessionLocal()
    try:
        repo = SQLAlchemyUserStatsRepository(db)
        ai_service = LLMFeedbackService()
        usecase = LearningSupportUseCase(repo, ai_service)
        deleted_count = usecase.cleanup_old_data()
        if deleted_count > 0:
            logger.info(f"Old history cleaned up: {deleted_count} records deleted.")
    except Exception as e:
        logger.error(f"Error during startup history cleanup: {e}")
    finally:
        db.close()

# アプリ起動時処理
@app.on_event("startup")
def startup_event():
    init_databases()
    run_startup_cleanup()

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

# おみくじの静的UIショートカットパス (便利アクセスのため)
@app.get("/omikuji-ui")
async def omikuji_ui():
    return FileResponse(os.path.join("static", "index.html"))

# ルーターの登録
app.include_router(habit_tracker.router, tags=["Habit Tracker"])
app.include_router(omikuji.router, tags=["Omikuji"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
