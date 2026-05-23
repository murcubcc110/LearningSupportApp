# app/infrastructure/repositories/sqlalchemy_user_stats_repository.py
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.entities.learning_support import UserStatsEntity, HistoryEntity
from app.domain.repositories.user_stats_repository import UserStatsRepository
from app.infrastructure.database.models.learning_support import UserStatsDB, HistoryDB

class SQLAlchemyUserStatsRepository(UserStatsRepository):
    """
    SQLAlchemyを使用したUserStatsRepositoryの実装 (Adapter)
    """
    def __init__(self, db: Session):
        self.db = db

    def _stats_to_entity(self, db_stats: UserStatsDB) -> UserStatsEntity:
        return UserStatsEntity(
            user_id=db_stats.user_id,
            consecutive_days=db_stats.consecutive_days,
            last_practice_date=db_stats.last_practice_date
        )

    def _history_to_entity(self, db_history: HistoryDB) -> HistoryEntity:
        return HistoryEntity(
            id=db_history.id,
            user_id=db_history.user_id,
            character_id=db_history.character_id,
            timestamp=db_history.timestamp,
            user_message=db_history.user_message,
            followed_plan=db_history.followed_plan,
            consecutive_days=db_history.consecutive_days,
            fortune=db_history.fortune,
            katsu=db_history.katsu,
            advice=db_history.advice,
            next_action_advice=db_history.next_action_advice
        )

    def get_by_user_id(self, user_id: str) -> Optional[UserStatsEntity]:
        db_stats = self.db.query(UserStatsDB).filter(UserStatsDB.user_id == user_id).first()
        if not db_stats:
            return None
        return self._stats_to_entity(db_stats)

    def save_stats(self, user_id: str, consecutive_days: int, last_practice_date: datetime) -> UserStatsEntity:
        db_stats = self.db.query(UserStatsDB).filter(UserStatsDB.user_id == user_id).first()
        if not db_stats:
            db_stats = UserStatsDB(user_id=user_id)
            self.db.add(db_stats)
        
        db_stats.consecutive_days = consecutive_days
        db_stats.last_practice_date = last_practice_date
        
        self.db.commit()
        self.db.refresh(db_stats)
        return self._stats_to_entity(db_stats)

    def get_recent_history(self, user_id: str, limit: int) -> List[HistoryEntity]:
        db_histories = self.db.query(HistoryDB).filter(
            HistoryDB.user_id == user_id
        ).order_by(HistoryDB.timestamp.desc()).limit(limit).all()
        # 古い順にするために逆順で返す
        db_histories.reverse()
        return [self._history_to_entity(h) for h in db_histories]

    def save_history(self, history: HistoryEntity) -> HistoryEntity:
        db_history = HistoryDB(
            user_id=history.user_id,
            character_id=history.character_id,
            timestamp=history.timestamp,
            user_message=history.user_message,
            followed_plan=history.followed_plan,
            consecutive_days=history.consecutive_days,
            fortune=history.fortune,
            katsu=history.katsu,
            advice=history.advice,
            next_action_advice=history.next_action_advice
        )
        self.db.add(db_history)
        self.db.commit()
        self.db.refresh(db_history)
        return self._history_to_entity(db_history)

    def delete_history_older_than(self, date_limit: datetime) -> int:
        try:
            deleted_count = self.db.query(HistoryDB).filter(HistoryDB.timestamp < date_limit).delete()
            self.db.commit()
            return deleted_count
        except Exception as e:
            self.db.rollback()
            raise e

    def run_vacuum(self) -> None:
        try:
            self.db.execute("VACUUM")
        except Exception:
            # SQLiteのVACUUMはトランザクション外で実行する必要がある場合があるため、エラー時は無視またはロールバック
            pass
