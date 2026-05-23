# app/api/endpoints/omikuji.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.domain.models import OmikujiRequest, OmikujiResponse, UserStats
from app.infrastructure.database.learning_support_db import get_db
from app.infrastructure.repositories.sqlalchemy_user_stats_repository import SQLAlchemyUserStatsRepository
from app.infrastructure.ai.llm_feedback_service import LLMFeedbackService
from app.usecases.learning_support.learning_support_usecase import LearningSupportUseCase

router = APIRouter()

# ユースケースの依存関係解決用の関数
def get_learning_support_usecase(db: Session = Depends(get_db)) -> LearningSupportUseCase:
    repository = SQLAlchemyUserStatsRepository(db)
    ai_service = LLMFeedbackService()
    return LearningSupportUseCase(repository, ai_service)

@router.post("/omikuji", response_model=OmikujiResponse)
async def get_omikuji(
    request: OmikujiRequest,
    usecase: LearningSupportUseCase = Depends(get_learning_support_usecase)
):
    try:
        history_entity = usecase.get_omikuji(
            user_id=request.user_id,
            character_id=request.character_id,
            consecutive_days=request.consecutive_days,
            followed_plan=request.followed_plan,
            user_message=request.user_message
        )
        return OmikujiResponse(
            fortune=history_entity.fortune,
            katsu=history_entity.katsu,
            advice=history_entity.advice,
            next_action_advice=history_entity.next_action_advice
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"御神託を得られませんでした: {str(e)}")

@router.get("/user/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: str,
    usecase: LearningSupportUseCase = Depends(get_learning_support_usecase)
):
    try:
        stats_entity = usecase.get_user_stats(user_id)
        return UserStats(
            user_id=stats_entity.user_id,
            consecutive_days=stats_entity.consecutive_days,
            last_practice_date=stats_entity.last_practice_date.isoformat() if stats_entity.last_practice_date else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ユーザー情報の取得に失敗しました: {str(e)}")

@router.put("/user/{user_id}/stats", response_model=UserStats)
async def update_user_stats(
    user_id: str,
    stats_update: UserStats,
    usecase: LearningSupportUseCase = Depends(get_learning_support_usecase)
):
    try:
        stats_entity = usecase.update_user_stats(user_id, stats_update.consecutive_days)
        return UserStats(
            user_id=stats_entity.user_id,
            consecutive_days=stats_entity.consecutive_days,
            last_practice_date=stats_entity.last_practice_date.isoformat() if stats_entity.last_practice_date else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ユーザー情報の更新に失敗しました: {str(e)}")
