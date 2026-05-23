# app/usecases/ports/ai_feedback_service.py
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from app.domain.entities.tracker import DailyRecordEntity

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
        character: str,
        current_user_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        習慣の進捗状況を分析し、AIフィードバックJSONテキストとカテゴリ(praise/scold/encourage/total_review)を返します。
        """
        pass
