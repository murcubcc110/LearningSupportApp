from pydantic import BaseModel, Field

class OmikujiRequest(BaseModel):
    user_id: str = Field(..., description="ユーザーの識別子")
    character_id: str = Field("ogami", description="キャラクターID (ogami or mio)")
    consecutive_days: int = Field(..., description="連続ログイン日数")
    followed_plan: bool = Field(..., description="計画通りに進められたか")
    user_message: str = Field(..., description="ユーザーの一言")

class OmikujiResponse(BaseModel):
    fortune: str = Field(..., description="運勢")
    katsu: str = Field(..., description="魂を揺さぶる一言")
    advice: str = Field(..., description="具体的な説教と励まし")
    next_action_advice: str = Field(..., description="計画を完遂するための具体的な次の一歩")

class UserStats(BaseModel):
    user_id: str
    consecutive_days: int
    last_practice_date: str = None
