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
                conn.execute(text("ALTER TABLE trackers ADD COLUMN character VARCHAR DEFAULT 'ai_ch_01'"))
                conn.commit()
            logger.info("Migration successful: added 'character' column to 'trackers'")
        else:
            with HTEngine.connect() as conn:
                conn.execute(text("UPDATE trackers SET character = 'ai_ch_01' WHERE character = 'ogami'"))
                conn.execute(text("UPDATE trackers SET character = 'ai_ch_02' WHERE character = 'mio'"))
                conn.commit()
            logger.info("Migration successful: updated 'character' column values to new IDs")
    except Exception as e:
        logger.error(f"Migration error: {e}")

    # キャラクター初期データシード
    db = HTSessionLocal()
    try:
        from app.core.prompts import SYSTEM_PROMPTS, COMMON_JSON_FORMAT
        
        # ai_ch_01 prompt excluding COMMON_JSON_FORMAT
        ogami_prompt = SYSTEM_PROMPTS["ai_ch_01"].replace(COMMON_JSON_FORMAT, "").strip()
        # ai_ch_02 prompt excluding COMMON_JSON_FORMAT
        mio_prompt = SYSTEM_PROMPTS["ai_ch_02"].replace(COMMON_JSON_FORMAT, "").strip()
        
        # 古いIDのキャラクターがあれば移行して削除する
        old_ogami = db.query(CharacterDB).filter(CharacterDB.id == "ogami").first()
        if old_ogami:
            logger.info("Found old character 'ogami'. Migrating to 'ai_ch_01'...")
            # 新しいIDで作成
            new_ogami = CharacterDB(
                id="ai_ch_01",
                name="巌狼",
                avatar_url=old_ogami.avatar_url,
                system_prompt=ogami_prompt
            )
            db.delete(old_ogami)
            db.commit()
            db.add(new_ogami)
            db.commit()

        old_mio = db.query(CharacterDB).filter(CharacterDB.id == "mio").first()
        if old_mio:
            logger.info("Found old character 'mio'. Migrating to 'ai_ch_02'...")
            # 新しいIDで作成
            new_mio = CharacterDB(
                id="ai_ch_02",
                name="こはる",
                avatar_url=old_mio.avatar_url,
                system_prompt=mio_prompt
            )
            db.delete(old_mio)
            db.commit()
            db.add(new_mio)
            db.commit()
        
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
            if ogami.name == "大神様":
                ogami.name = "巌狼"
                logger.info("Database migration: updated ai_ch_01 name to default.")
            if ogami.avatar_url == "/static/ogami_sama.png":
                ogami.avatar_url = "/static/genro.png"
                logger.info("Database migration: updated ai_ch_01 avatar_url to /static/genro.png.")
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
            if mio.name == "ミオ":
                mio.name = "こはる"
                logger.info("Database migration: updated ai_ch_02 name to default.")
            if mio.avatar_url == "/static/mio.png":
                mio.avatar_url = "/static/koharu.png"
                logger.info("Database migration: updated ai_ch_02 avatar_url to /static/koharu.png.")
            mio.system_prompt = mio_prompt
            db.add(mio)
            
        db.commit()
    except Exception as e:
        logger.error(f"Error seeding/migrating characters: {e}")
        db.rollback()
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
