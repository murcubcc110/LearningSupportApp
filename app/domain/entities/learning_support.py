# app/domain/entities/learning_support.py
from datetime import datetime
from typing import Optional

class UserStatsEntity:
    """
    純粋なドメインエンティティ：ユーザー学習統計
    """
    def __init__(self, user_id: str, consecutive_days: int, last_practice_date: Optional[datetime]):
        self.user_id = user_id
        self.consecutive_days = consecutive_days
        self.last_practice_date = last_practice_date


class HistoryEntity:
    """
    純粋なドメインエンティティ：おみくじ対話履歴
    """
    def __init__(
        self,
        id: Optional[int],
        user_id: str,
        character_id: str,
        timestamp: datetime,
        user_message: str,
        followed_plan: bool,
        consecutive_days: int,
        fortune: str,
        katsu: str,
        advice: str,
        next_action_advice: str
    ):
        self.id = id
        self.user_id = user_id
        self.character_id = character_id
        self.timestamp = timestamp
        self.user_message = user_message
        self.followed_plan = followed_plan
        self.consecutive_days = consecutive_days
        self.fortune = fortune
        self.katsu = katsu
        self.advice = advice
        self.next_action_advice = next_action_advice
