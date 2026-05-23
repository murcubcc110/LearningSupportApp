# app/infrastructure/repositories/sqlalchemy_tracker_repository.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.domain.entities.tracker import TrackerEntity, DailyRecordEntity
from app.domain.repositories.tracker_repository import TrackerRepository
from app.infrastructure.database.models.habit_tracker import TrackerDB, DailyRecordDB

class SQLAlchemyTrackerRepository(TrackerRepository):
    """
    SQLAlchemyを使用したTrackerRepositoryの実装 (Adapter)
    """
    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, db_tracker: TrackerDB) -> TrackerEntity:
        records = [
            DailyRecordEntity(
                id=r.id,
                tracker_id=r.tracker_id,
                day_number=r.day_number,
                status=r.status,
                recorded_at=r.recorded_at
            ) for r in db_tracker.records
        ]
        return TrackerEntity(
            id=db_tracker.id,
            title=db_tracker.title,
            period_days=db_tracker.period_days,
            start_date=db_tracker.start_date,
            is_active=db_tracker.is_active,
            created_at=db_tracker.created_at,
            ai_comment=db_tracker.ai_comment,
            ai_status=db_tracker.ai_status,
            character=db_tracker.character,
            records=records
        )

    def get_by_id(self, tracker_id: int) -> Optional[TrackerEntity]:
        db_tracker = self.db.query(TrackerDB).filter(TrackerDB.id == tracker_id).first()
        if not db_tracker:
            return None
        return self._to_entity(db_tracker)

    def get_all(self) -> List[TrackerEntity]:
        db_trackers = self.db.query(TrackerDB).all()
        return [self._to_entity(t) for t in db_trackers]

    def save(self, tracker: TrackerEntity) -> TrackerEntity:
        if tracker.id is not None:
            # 既存のトラッカーの更新
            db_tracker = self.db.query(TrackerDB).filter(TrackerDB.id == tracker.id).first()
            if not db_tracker:
                raise ValueError(f"Tracker with id {tracker.id} not found")
            
            db_tracker.title = tracker.title
            db_tracker.period_days = tracker.period_days
            db_tracker.is_active = tracker.is_active
            db_tracker.ai_comment = tracker.ai_comment
            db_tracker.ai_status = tracker.ai_status
            db_tracker.character = tracker.character
            
            # レコードのステータスの更新
            for record_entity in tracker.records:
                db_record = self.db.query(DailyRecordDB).filter(
                    DailyRecordDB.tracker_id == tracker.id,
                    DailyRecordDB.day_number == record_entity.day_number
                ).first()
                if db_record:
                    db_record.status = record_entity.status
        else:
            # 新規トラッカーの作成
            db_tracker = TrackerDB(
                title=tracker.title,
                period_days=tracker.period_days,
                start_date=tracker.start_date,
                is_active=tracker.is_active,
                created_at=tracker.created_at,
                ai_comment=tracker.ai_comment,
                ai_status=tracker.ai_status,
                character=tracker.character
            )
            self.db.add(db_tracker)
            self.db.flush()  # IDを発行するためにDBに一時反映
            
            # 日々の空のレコードの作成
            for record_entity in tracker.records:
                db_record = DailyRecordDB(
                    tracker_id=db_tracker.id,
                    day_number=record_entity.day_number,
                    status=record_entity.status,
                    recorded_at=record_entity.recorded_at
                )
                self.db.add(db_record)
        
        self.db.commit()
        self.db.refresh(db_tracker)
        return self._to_entity(db_tracker)

    def delete(self, tracker_id: int) -> bool:
        db_tracker = self.db.query(TrackerDB).filter(TrackerDB.id == tracker_id).first()
        if not db_tracker:
            return False
        self.db.delete(db_tracker)
        self.db.commit()
        return True

    def update_record_status(self, tracker_id: int, day_number: int, status: str) -> Optional[DailyRecordEntity]:
        db_record = self.db.query(DailyRecordDB).filter(
            DailyRecordDB.tracker_id == tracker_id,
            DailyRecordDB.day_number == day_number
        ).first()
        if not db_record:
            return None
        db_record.status = status
        self.db.commit()
        self.db.refresh(db_record)
        
        return DailyRecordEntity(
            id=db_record.id,
            tracker_id=db_record.tracker_id,
            day_number=db_record.day_number,
            status=db_record.status,
            recorded_at=db_record.recorded_at
        )
