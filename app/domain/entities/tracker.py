# app/domain/entities/tracker.py
from datetime import date, datetime
from typing import List, Optional

class DailyRecordEntity:
    """
    純粋なドメインエンティティ：日々の達成状況記録
    特定の日の達成状況（pending, achieved, slacked）を表します。
    """
    def __init__(
        self,
        id: Optional[int],
        tracker_id: int,
        day_number: int,
        status: str,
        recorded_at: datetime
    ):
        self.id = id
        self.tracker_id = tracker_id
        self.day_number = day_number
        self.status = status  # "pending", "achieved", "slacked"
        self.recorded_at = recorded_at


class TrackerEntity:
    """
    純粋なドメインエンティティ：習慣トラッカー
    習慣チャレンジ全体の設定と状態、および日々の記録を保持します。
    """
    def __init__(
        self,
        id: Optional[int],
        title: str,
        period_days: int,
        start_date: date,
        is_active: bool,
        created_at: datetime,
        ai_comment: Optional[str],
        ai_status: Optional[str],
        character: str,
        records: List[DailyRecordEntity] = None
    ):
        self.id = id
        self.title = title
        self.period_days = period_days
        self.start_date = start_date
        self.is_active = is_active
        self.created_at = created_at
        self.ai_comment = ai_comment
        self.ai_status = ai_status
        self.character = character
        self.records = records or []

    def calculate_stats(self) -> dict:
        """
        トラッカーの現在の進捗状況から統計情報を計算するドメインビジネスロジック。
        """
        total_days = self.period_days
        achieved_days = sum(1 for r in self.records if r.status == "achieved")
        slacked_days = sum(1 for r in self.records if r.status == "slacked")
        recorded_days = achieved_days + slacked_days
        
        # 達成率 (達成した日数 / 設定された期間)
        rate = round((achieved_days / total_days) * 100) if total_days > 0 else 0
        # 進捗率 (記録完了した日数 / 設定された期間)
        progress_percent = round((recorded_days / total_days) * 100) if total_days > 0 else 0
        
        # 最大連続達成日数 (streak) の計算
        sorted_records = sorted(self.records, key=lambda r: r.day_number)
        max_streak = 0
        current_streak = 0
        for r in sorted_records:
            if r.status == "achieved":
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0
                
        return {
            "achieved_days": achieved_days,
            "slacked_days": slacked_days,
            "rate": rate,
            "progress_percent": progress_percent,
            "streak": max_streak
        }
