# app/usecases/tracker/tracker_usecase.py
from typing import List, Optional, Tuple
from datetime import date, datetime
from app.domain.entities.tracker import TrackerEntity, DailyRecordEntity
from app.domain.repositories.tracker_repository import TrackerRepository
from app.usecases.ports.ai_feedback_service import AIFeedbackService

class TrackerUseCase:
    """
    習慣トラッカーアプリケーションのユースケース層 (Application Service)
    """
    def __init__(self, repository: TrackerRepository, ai_service: AIFeedbackService):
        self.repository = repository
        self.ai_service = ai_service

    def get_all_trackers(self) -> List[TrackerEntity]:
        """全トラッカーを作成日時の降順で取得します"""
        trackers = self.repository.get_all()
        return sorted(trackers, key=lambda t: t.created_at, reverse=True)

    def get_tracker_by_id(self, tracker_id: int) -> Optional[TrackerEntity]:
        """ID指定でトラッカーを取得します"""
        return self.repository.get_by_id(tracker_id)

    def create_tracker(self, title: str, period_days: int) -> TrackerEntity:
        """新しい習慣チャレンジを作成し、期間分の未入力レコードを自動生成します"""
        if period_days < 1 or period_days > 14:
            raise ValueError("期間は1日から14日間の範囲で設定してください。")

        # トラッカーエンティティの初期化
        new_tracker = TrackerEntity(
            id=None,
            title=title,
            period_days=period_days,
            start_date=date.today(),
            is_active=True,
            created_at=datetime.now(),
            ai_comment="新しいチャレンジが始まりました！まずは1日目を達成して、好スタートを切りましょう！🚀",
            ai_status="encourage",
            character="ai_ch_01"
        )
        
        # 1日から設定期間分の日々の記録を「未入力」の状態で生成
        records = []
        for day in range(1, period_days + 1):
            record = DailyRecordEntity(
                id=None,
                tracker_id=0, # 後ほどDB側で設定される
                day_number=day,
                status="pending",
                recorded_at=datetime.now()
            )
            records.append(record)
            
        new_tracker.records = records
        return self.repository.save(new_tracker)

    def update_record(self, tracker_id: int, day_number: int, status: str, user_message: Optional[str] = None) -> Optional[TrackerEntity]:
        """特定日のステータスを更新し、全履歴に基づきAIフィードバックを再生成します"""
        if status not in ["achieved", "slacked", "pending"]:
            raise ValueError("無効なステータス値です。")

        tracker = self.repository.get_by_id(tracker_id)
        if not tracker:
            return None

        # 日々の達成状況を更新（一言コメントも一緒に記録）
        self.repository.update_record_status(tracker_id, day_number, status, user_message)
        
        # 最新のレコード一覧を再ロード
        updated_tracker = self.repository.get_by_id(tracker_id)
        if not updated_tracker:
            return None

        # AIフィードバックコメントとステータス種別を再生成
        ai_comment, ai_status = self.ai_service.generate_habit_feedback(
            tracker_title=updated_tracker.title,
            period_days=updated_tracker.period_days,
            records=updated_tracker.records,
            character=updated_tracker.character,
            current_user_message=user_message
        )

        # トラッカー側のAIコメント情報を更新
        updated_tracker.ai_comment = ai_comment
        updated_tracker.ai_status = ai_status
        
        return self.repository.save(updated_tracker)

    def update_character(self, tracker_id: int, character: str) -> Optional[TrackerEntity]:
        """キャラクター（巌狼/こはる）を切り替え、AIアドバイスを再計算します"""
        if character not in ["ai_ch_01", "ai_ch_02"]:
            raise ValueError("無効なキャラクター値です。")

        tracker = self.repository.get_by_id(tracker_id)
        if not tracker:
            return None

        tracker.character = character
        
        # キャラクター変更に伴い、AIフィードバックコメントとステータスを再生成
        ai_comment, ai_status = self.ai_service.generate_habit_feedback(
            tracker_title=tracker.title,
            period_days=tracker.period_days,
            records=tracker.records,
            character=tracker.character
        )

        tracker.ai_comment = ai_comment
        tracker.ai_status = ai_status

        return self.repository.save(tracker)

    def toggle_tracker_active(self, tracker_id: int) -> Optional[TrackerEntity]:
        """チャレンジのアクティブ / 非アクティブ (終了) 状態を切り替えます"""
        tracker = self.repository.get_by_id(tracker_id)
        if not tracker:
            return None

        tracker.is_active = not tracker.is_active
        return self.repository.save(tracker)

    def delete_tracker(self, tracker_id: int) -> bool:
        """習慣チャレンジを削除します"""
        return self.repository.delete(tracker_id)
