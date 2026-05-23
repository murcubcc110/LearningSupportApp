# app/usecases/learning_support/learning_support_usecase.py
from datetime import datetime, timedelta
from typing import Optional
from app.domain.entities.learning_support import UserStatsEntity, HistoryEntity
from app.domain.repositories.user_stats_repository import UserStatsRepository
from app.usecases.ports.ai_feedback_service import AIFeedbackService

class LearningSupportUseCase:
    """
    おみくじ・学習継続支援アプリケーションのユースケース層 (Application Service)
    """
    def __init__(self, repository: UserStatsRepository, ai_service: AIFeedbackService):
        self.repository = repository
        self.ai_service = ai_service

    def get_omikuji(
        self,
        user_id: str,
        character_id: str,
        consecutive_days: int,
        followed_plan: bool,
        user_message: str
    ) -> HistoryEntity:
        """
        おみくじ御神託を生成し、履歴と学習統計を更新して結果を返します。
        """
        # 直近の履歴を3件取得
        history = self.repository.get_recent_history(user_id, limit=3)

        # AIフィードバックサービスを使用して御神託を生成
        fortune, katsu, advice, next_action_advice = self.ai_service.generate_omikuji_feedback(
            character_id=character_id,
            consecutive_days=consecutive_days,
            followed_plan=followed_plan,
            user_message=user_message,
            history=history
        )

        # 履歴エンティティの生成
        new_history = HistoryEntity(
            id=None,
            user_id=user_id,
            character_id=character_id,
            timestamp=datetime.now(),
            user_message=user_message,
            followed_plan=followed_plan,
            consecutive_days=consecutive_days,
            fortune=fortune,
            katsu=katsu,
            advice=advice,
            next_action_advice=next_action_advice
        )

        # 履歴の保存
        saved_history = self.repository.save_history(new_history)

        # 統計（継続日数）の更新
        self.repository.save_stats(
            user_id=user_id,
            consecutive_days=consecutive_days,
            last_practice_date=datetime.now()
        )

        return saved_history

    def get_user_stats(self, user_id: str) -> UserStatsEntity:
        """ユーザーID指定で学習統計情報を取得、または新規初期値を返します"""
        stats = self.repository.get_by_user_id(user_id)
        if not stats:
            return UserStatsEntity(user_id=user_id, consecutive_days=0, last_practice_date=None)
            
        current_days = stats.consecutive_days
        last_date = stats.last_practice_date.date() if stats.last_practice_date else None
        today = datetime.now().date()
        
        suggested_days = current_days
        if last_date:
            delta = (today - last_date).days
            if delta == 1:
                suggested_days = current_days + 1
            elif delta > 1:
                suggested_days = 1
                
        return UserStatsEntity(
            user_id=user_id,
            consecutive_days=suggested_days,
            last_practice_date=stats.last_practice_date
        )

    def update_user_stats(self, user_id: str, consecutive_days: int) -> UserStatsEntity:
        """ユーザー学習統計情報を直接更新します"""
        return self.repository.save_stats(
            user_id=user_id,
            consecutive_days=consecutive_days,
            last_practice_date=datetime.now()
        )

    def cleanup_old_data(self) -> int:
        """3ヶ月以上前の履歴データを削除し、データベースを最適化します"""
        three_months_ago = datetime.now() - timedelta(days=90)
        deleted_count = self.repository.delete_history_older_than(three_months_ago)
        if deleted_count > 0:
            self.repository.run_vacuum()
        return deleted_count
