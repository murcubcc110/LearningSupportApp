# app/api/dtos/habit_tracker_dto.py
from pydantic import BaseModel, Field

from typing import Optional

class RecordUpdateDTO(BaseModel):
    """日々の記録の更新リクエストDTO"""
    status: str = Field(..., description="新しい達成状況 ('achieved', 'slacked', 'pending')")
    user_message: Optional[str] = Field(None, description="ユーザーの今の一言 (愚痴、困り事、今の気持ち)")


class CharacterUpdateDTO(BaseModel):
    """キャラクター更新リクエストDTO"""
    character: str = Field(..., description="選択されたキャラクター ('ai_ch_01', 'ai_ch_02')")
