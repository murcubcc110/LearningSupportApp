# app/domain/repositories/user_stats_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from app.domain.entities.learning_support import UserStatsEntity, HistoryEntity

class UserStatsRepository(ABC):
    """
    おみくじ・学習継続支援統計用リポジトリの抽象インターフェース (Port)
    """
    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[UserStatsEntity]:
        pass

    @abstractmethod
    def save_stats(self, user_id: str, consecutive_days: int, last_practice_date: datetime) -> UserStatsEntity:
        pass

    @abstractmethod
    def get_recent_history(self, user_id: str, limit: int) -> List[HistoryEntity]:
        pass

    @abstractmethod
    def save_history(self, history: HistoryEntity) -> HistoryEntity:
        pass

    @abstractmethod
    def delete_history_older_than(self, date_limit: datetime) -> int:
        pass

    @abstractmethod
    def run_vacuum(self) -> None:
        pass
