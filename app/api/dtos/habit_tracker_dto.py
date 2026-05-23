# app/api/dtos/habit_tracker_dto.py
from pydantic import BaseModel, Field

class RecordUpdateDTO(BaseModel):
    """日々の記録の更新リクエストDTO"""
    status: str = Field(..., description="新しい達成状況 ('achieved', 'slacked', 'pending')")


class CharacterUpdateDTO(BaseModel):
    """キャラクター更新リクエストDTO"""
    character: str = Field(..., description="選択されたキャラクター ('ai_ch_01', 'ai_ch_02')")
