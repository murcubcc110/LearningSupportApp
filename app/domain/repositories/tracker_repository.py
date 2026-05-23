# app/domain/repositories/tracker_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.tracker import TrackerEntity, DailyRecordEntity

class TrackerRepository(ABC):
    """
    習慣トラッカー用リポジトリの抽象インターフェース (Port)
    """
    @abstractmethod
    def get_by_id(self, tracker_id: int) -> Optional[TrackerEntity]:
        pass

    @abstractmethod
    def get_all(self) -> List[TrackerEntity]:
        pass

    @abstractmethod
    def save(self, tracker: TrackerEntity) -> TrackerEntity:
        pass

    @abstractmethod
    def delete(self, tracker_id: int) -> bool:
        pass

    @abstractmethod
    def update_record_status(self, tracker_id: int, day_number: int, status: str) -> Optional[DailyRecordEntity]:
        pass
