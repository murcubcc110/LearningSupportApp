# app/api/endpoints/habit_tracker.py
import json
import logging
import os
import shutil
from fastapi import APIRouter, Depends, Form, Request, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.infrastructure.database.habit_tracker_db import get_db
from app.infrastructure.database.models.habit_tracker import CharacterDB
from app.infrastructure.repositories.sqlalchemy_tracker_repository import SQLAlchemyTrackerRepository
from app.infrastructure.ai.llm_feedback_service import LLMFeedbackService
from app.usecases.tracker.tracker_usecase import TrackerUseCase
from app.api.dtos.habit_tracker_dto import RecordUpdateDTO, CharacterUpdateDTO

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ユースケースの依存関係解決用の関数
def get_tracker_usecase(db: Session = Depends(get_db)) -> TrackerUseCase:
    repository = SQLAlchemyTrackerRepository(db)
    ai_service = LLMFeedbackService()
    return TrackerUseCase(repository, ai_service)

# AIコメントのパース用ユーティリティ
def parse_ai_comment(ai_comment: str) -> dict:
    try:
        data = json.loads(ai_comment)
        if not isinstance(data, dict):
            return {
                "fortune": "吉",
                "katsu": "さあ、始めよう！",
                "advice": str(ai_comment),
                "next_action_advice": "まずは最初の一歩を踏み出しましょう。"
            }
        return {
            "fortune": data.get("fortune", "吉"),
            "katsu": data.get("katsu", "さあ、始めよう！"),
            "advice": data.get("advice", ""),
            "next_action_advice": data.get("next_action_advice", "")
        }
    except Exception:
        return {
            "fortune": "吉",
            "katsu": "さあ、始めよう！",
            "advice": ai_comment or "新しいチャレンジが始まりました！",
            "next_action_advice": "まずは一歩を踏み出しましょう。"
        }


# ==========================================
# 1. メイン画面 (GET /)
# ==========================================
@router.get("/")
def read_root(
    request: Request,
    tracker_id: int = None,
    db: Session = Depends(get_db),
    usecase: TrackerUseCase = Depends(get_tracker_usecase)
):
    trackers = usecase.get_all_trackers()
    active_tracker = None
    stats = None
    
    if trackers:
        if tracker_id:
            active_tracker = usecase.get_tracker_by_id(tracker_id)
        if not active_tracker:
            active_tracker = next((t for t in trackers if t.is_active), trackers[0])
            
        if active_tracker:
            stats = active_tracker.calculate_stats()

    if active_tracker:
        ai_comment_parsed = parse_ai_comment(active_tracker.ai_comment)
    else:
        ai_comment_parsed = {
            "fortune": "吉",
            "katsu": "さあ、始めよう！",
            "advice": "習慣化チャレンジを始めましょう！",
            "next_action_advice": "まずは最初の一歩を踏み出しましょう。"
        }

    # データベースからキャラクター設定マップを取得
    characters_db = db.query(CharacterDB).all()
    characters_map = {c.id: c for c in characters_db}
    
    # 万が一シードデータが存在しない場合のフォールバック用ダミークラス
    if "ai_ch_01" not in characters_map:
        class DummyChar:
            def __init__(self, name, avatar_url):
                self.name = name
                self.avatar_url = avatar_url
        characters_map["ai_ch_01"] = DummyChar("巌狼", "/static/ogami_sama.png")
        characters_map["ai_ch_02"] = DummyChar("こはる", "/static/mio.png")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "trackers": trackers,
            "active_tracker": active_tracker,
            "stats": stats,
            "ai_comment_parsed": ai_comment_parsed,
            "characters_map": characters_map
        }
    )


# ==========================================
# 2. 新規チャレンジ作成 (POST /tracker/create)
# ==========================================
@router.post("/tracker/create")
def create_tracker(
    title: str = Form(...), 
    period_days: int = Form(...), 
    usecase: TrackerUseCase = Depends(get_tracker_usecase)
):
    try:
        new_tracker = usecase.create_tracker(title, period_days)
        return RedirectResponse(url=f"/?tracker_id={new_tracker.id}", status_code=303)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# ==========================================
# 3. 日々の記録の更新 (POST /tracker/{id}/record/{day})
# ==========================================
@router.post("/tracker/{tracker_id}/record/{day_number}")
def update_record(
    tracker_id: int, 
    day_number: int, 
    payload: RecordUpdateDTO, 
    db: Session = Depends(get_db),
    usecase: TrackerUseCase = Depends(get_tracker_usecase)
):
    try:
        updated_tracker = usecase.update_record(tracker_id, day_number, payload.status)
        if not updated_tracker:
            raise HTTPException(status_code=404, detail="トラッカーまたはレコードが見つかりません。")
            
        stats = updated_tracker.calculate_stats()
        
        char_db = db.query(CharacterDB).filter(CharacterDB.id == updated_tracker.character).first()
        char_name = char_db.name if char_db else ("こはる" if updated_tracker.character == "ai_ch_02" else "巌狼")
        char_avatar = char_db.avatar_url if char_db else ("/static/mio.png" if updated_tracker.character == "ai_ch_02" else "/static/ogami_sama.png")
        
        return JSONResponse(content={
            "status": "success",
            "character": updated_tracker.character,
            "character_name": char_name,
            "character_avatar": char_avatar,
            "ai_comment": updated_tracker.ai_comment,
            "ai_comment_parsed": parse_ai_comment(updated_tracker.ai_comment),
            "ai_status": updated_tracker.ai_status,
            "stats": stats
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# 3.5. キャラクターの更新 (POST /tracker/{id}/character)
# ==========================================
@router.post("/tracker/{tracker_id}/character")
def update_character(
    tracker_id: int,
    payload: CharacterUpdateDTO,
    db: Session = Depends(get_db),
    usecase: TrackerUseCase = Depends(get_tracker_usecase)
):
    try:
        updated_tracker = usecase.update_character(tracker_id, payload.character)
        if not updated_tracker:
            raise HTTPException(status_code=404, detail="トラッカーが見つかりません。")
            
        stats = updated_tracker.calculate_stats()
        
        char_db = db.query(CharacterDB).filter(CharacterDB.id == updated_tracker.character).first()
        char_name = char_db.name if char_db else ("こはる" if updated_tracker.character == "ai_ch_02" else "巌狼")
        char_avatar = char_db.avatar_url if char_db else ("/static/mio.png" if updated_tracker.character == "ai_ch_02" else "/static/ogami_sama.png")
        
        return JSONResponse(content={
            "status": "success",
            "character": updated_tracker.character,
            "character_name": char_name,
            "character_avatar": char_avatar,
            "ai_comment": updated_tracker.ai_comment,
            "ai_comment_parsed": parse_ai_comment(updated_tracker.ai_comment),
            "ai_status": updated_tracker.ai_status,
            "stats": stats
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# 4. チャレンジ状態トグル (POST /tracker/{id}/toggle-active)
# ==========================================
@router.post("/tracker/{tracker_id}/toggle-active")
def toggle_tracker_active(
    tracker_id: int,
    usecase: TrackerUseCase = Depends(get_tracker_usecase)
):
    # ロギング用デバッグ処理
    import datetime
    log_file = "toggle_debug.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"--- Toggle event at {datetime.datetime.now()} ---\n")
        f.write(f"Requested tracker_id: {tracker_id}\n")

    updated_tracker = usecase.toggle_tracker_active(tracker_id)
    if not updated_tracker:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("Error: Tracker not found\n")
        raise HTTPException(status_code=404, detail="トラッカーが見つかりません。")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"Found tracker title: {updated_tracker.title}\n")
        f.write(f"After commit & refresh is_active: {updated_tracker.is_active}\n")

    return RedirectResponse(url=f"/?tracker_id={tracker_id}", status_code=303)


# ==========================================
# 5. チャレンジ削除 (POST /tracker/{id}/delete)
# ==========================================
@router.post("/tracker/{tracker_id}/delete")
def delete_tracker(
    tracker_id: int,
    usecase: TrackerUseCase = Depends(get_tracker_usecase)
):
    success = usecase.delete_tracker(tracker_id)
    if not success:
        raise HTTPException(status_code=404, detail="トラッカーが見つかりません。")
    return RedirectResponse(url="/", status_code=303)


# ==========================================
# 6. キャラクター一覧の取得 (GET /tracker/characters)
# ==========================================
@router.get("/tracker/characters")
def get_characters(db: Session = Depends(get_db)):
    characters = db.query(CharacterDB).all()
    return [{
        "id": c.id,
        "name": c.name,
        "avatar_url": c.avatar_url,
        "system_prompt": c.system_prompt
    } for c in characters]


# ==========================================
# 7. キャラクター設定の更新 (POST /tracker/characters/{character_id})
# ==========================================
@router.post("/tracker/characters/{character_id}")
async def update_character_settings(
    character_id: str,
    name: str = Form(...),
    system_prompt: str = Form(...),
    avatar_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    character = db.query(CharacterDB).filter(CharacterDB.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません。")

    character.name = name
    character.system_prompt = system_prompt

    # アバターファイルのアップロード処理
    if avatar_file and avatar_file.filename:
        # ディレクトリの作成
        upload_dir = os.path.join("static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # 拡張子の取得とファイル名の決定
        ext = os.path.splitext(avatar_file.filename)[1]
        # 重複を避けるため、キャラクターIDに応じたファイル名で保存
        filename = f"{character_id}{ext}"
        filepath = os.path.join(upload_dir, filename)

        try:
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(avatar_file.file, buffer)
            # avatar_url を更新 (例: /static/uploads/ogami.png)
            character.avatar_url = f"/static/uploads/{filename}"
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(status_code=500, detail="ファイルの保存に失敗しました。")

    db.commit()
    db.refresh(character)

    return JSONResponse(content={
        "status": "success",
        "character": {
            "id": character.id,
            "name": character.name,
            "avatar_url": character.avatar_url,
            "system_prompt": character.system_prompt
        }
    })


# ==========================================
# 8. キャラクター設定の初期化 (POST /tracker/characters/{character_id}/reset)
# ==========================================
@router.post("/tracker/characters/{character_id}/reset")
def reset_character_settings(
    character_id: str,
    db: Session = Depends(get_db)
):
    character = db.query(CharacterDB).filter(CharacterDB.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません。")

    from app.core.prompts import SYSTEM_PROMPTS, COMMON_JSON_FORMAT

    if character_id == "ai_ch_01":
        character.name = "巌狼"
        character.avatar_url = "/static/ogami_sama.png"
        character.system_prompt = SYSTEM_PROMPTS["ai_ch_01"].replace(COMMON_JSON_FORMAT, "").strip()
    elif character_id == "ai_ch_02":
        character.name = "こはる"
        character.avatar_url = "/static/mio.png"
        character.system_prompt = SYSTEM_PROMPTS["ai_ch_02"].replace(COMMON_JSON_FORMAT, "").strip()
    else:
        raise HTTPException(status_code=400, detail="無効なキャラクターIDです。")

    db.commit()
    db.refresh(character)

    return JSONResponse(content={
        "status": "success",
        "character": {
            "id": character.id,
            "name": character.name,
            "avatar_url": character.avatar_url,
            "system_prompt": character.system_prompt
        }
    })

