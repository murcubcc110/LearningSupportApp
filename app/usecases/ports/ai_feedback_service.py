# app/usecases/ports/ai_feedback_service.py
from abc import ABC, abstractmethod
from typing import List, Tuple
from app.domain.entities.tracker import DailyRecordEntity
from app.domain.entities.learning_support import HistoryEntity

class AIFeedbackService(ABC):
    """
    AIフィードバック生成サービス用インターフェース (Port)
    """
    @abstractmethod
    def generate_habit_feedback(
        self,
        tracker_title: str,
        period_days: int,
        records: List[DailyRecordEntity],
        character: str
    ) -> Tuple[str, str]:
        """
        習慣の進捗状況を分析し、AIフィードバックJSONテキストとカテゴリ(praise/scold/encourage/total_review)を返します。
        """
        pass

    @abstractmethod
    def generate_omikuji_feedback(
        self,
        character_id: str,
        consecutive_days: int,
        followed_plan: bool,
        user_message: str,
        history: List[HistoryEntity]
    ) -> Tuple[str, str, str, str]:
        """
        おみくじ対話の状況からAIアドバイスを生成し、
        (fortune, katsu, advice, next_action_advice) を返します。
        """
        pass
