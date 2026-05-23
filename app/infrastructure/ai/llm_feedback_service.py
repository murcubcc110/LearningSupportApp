# app/infrastructure/ai/llm_feedback_service.py
import os
import random
import json
import logging
from typing import List, Tuple
from app.domain.entities.tracker import DailyRecordEntity
from app.domain.entities.learning_support import HistoryEntity
from app.usecases.ports.ai_feedback_service import AIFeedbackService
from app.infrastructure.llm_client import LLMClient
from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPTS, COMMON_JSON_FORMAT
from app.infrastructure.database.habit_tracker_db import SessionLocal
from app.infrastructure.database.models.habit_tracker import CharacterDB

logger = logging.getLogger(__name__)

class LLMFeedbackService(AIFeedbackService):
    """
    LLM (OpenAI/Local LLM) を使用したAIフィードバック生成サービスの実装 (Adapter)
    接続失敗やパース失敗時には高品質なキャラクター固有のルールベース応答にフォールバックします。
    """
    
    # --- 大神様 (ogami) ルールベーステンプレート ---
    OGAMI_PRAISE = [
        {"fortune": "大吉", "katsu": "実に見事だ！我も称賛してやろう！🐺", "advice": "5日連続達成とは、貴様の意志も捨てたものではないな。この調子で栄光のゴールへ突き進むが良い！", "next_action_advice": "この勢いを止めるな。明日も決まった時間にPCの前に座るのだ！"},
        {"fortune": "大吉", "katsu": "圧倒的継続！白狼の加護を授けよう！✨", "advice": "5日連続でやり遂げるとはな。貴様の心に潜む甘えを完全に克服しつつある。この光り輝く記録を汚すことのないよう、精進せよ！", "next_action_advice": "明日の朝一番に、今日の成功要因を手帳に書き留めておくのだ！"}
    ]
    OGAMI_SCOLD = [
        {"fortune": "凶", "katsu": "喝ッ！惰眠を貪るつもりか！⚡", "advice": "何がサボりだ！昨日の自分との約束を破って恥ずかしくないのか？ここで諦めるなら、貴様の未来などそこまでだ！", "next_action_advice": "言い訳は無用。今すぐ明日の予定をカレンダーに書き込み、二度とサボるな！"},
        {"fortune": "凶", "katsu": "甘えるな！ここで退けばただの敗者だ！🔥", "advice": "未達成の赤文字が目に染みるわ。少し疲れたなどと言い訳をするな！我は貴様の甘えを断ち切るためにいる。明日は絶対に『達成』を勝ち取れ！", "next_action_advice": "今すぐ机の周りを整理し、明日すぐ作業に入れるようにセットせよ！"}
    ]
    OGAMI_ENCOURAGE = [
        {"fortune": "吉", "katsu": "一歩一歩、地道に進むが良い。🐾", "advice": "着実に歩みを進めているようだな。習慣化とは、己を鍛える日々の修練なり。完璧でなくとも、歩みを止めることなかれ。怠らず励めよ。", "next_action_advice": "小さな行動を続けるのだ。明日の分も手帳に書いておけ。"},
        {"fortune": "小吉", "katsu": "焦るな、継続こそが真の力となる。⭐", "advice": "フン、まあまあ順調なようだな。焦って一度に多くをやろうとせず、決めた分量を淡々とこなすがよい。我は常に見守っているぞ。", "next_action_advice": "明日の目標を半分にしてでも、実行する時間だけは確保せよ。"}
    ]
    OGAMI_TOTAL_REVIEW_HIGH = [
        {"fortune": "大吉", "katsu": "天晴れだ！貴様の執念、我の想像を超えたぞ！🐺", "advice": "全日程の記録を終えたな。達成率80%以上とは驚異的だ。最初は頼りなかった貴様が、これほど立派に習慣を成し遂げるとは。我も誇らしく思うぞ。この経験は必ず貴様の血肉となる！", "next_action_advice": "成し遂げた己を褒め称え、間髪入れずに次の高みを目指す新たな計画を立てよ！"}
    ]
    OGAMI_TOTAL_REVIEW_LOW = [
        {"fortune": "凶", "katsu": "終幕！だがこの結果で満足しているわけではあるまいな！🔥", "advice": "すべての記録が終わったが、達成率80%未満とは何事だ。サボった日々の重みを今一度噛み締めるが良い。だが、途中で投げ出さずに最後まで記録しきった執念だけは認めてやる。次こそは完全なる勝利を掴み取るのだ！", "next_action_advice": "今回の敗因（サボりグセ）をノートに書き出し、明日から新たな闘い（再チャレンジ）を開始せよ！"}
    ]

    # --- ミオ (mio) ルールベーステンプレート ---
    MIO_PRAISE = [
        {"fortune": "大吉", "katsu": "すごいやん！うちもめっちゃ嬉しいわ！🌸", "advice": "5日連続達成やね！ほんまにキミは頑張り屋さんやなぁ。毎日コツコツ続けるんは大変やったやろうに、偉い！自分をいーっぱい褒めてあげね。", "next_action_advice": "明日も無理のない範囲で、お茶でも飲みながら一緒に進めていこな。"},
        {"fortune": "大吉", "katsu": "パーフェクト！キミの努力が満開やね！🌺", "advice": "うわぁ、5日間も連続で！キミの頑張る姿を見てて、うちまで心がポカポカしてきたわぁ。習慣のご褒備に、今日はちょっと甘いものでも食べよか？", "next_action_advice": "明日はスタート前に、深呼吸を3回してリラックスして取り組んでみてね。"}
    ]
    MIO_SCOLD = [
        {"fortune": "末吉", "katsu": "こらこら、お休みしちゃった？🍵", "advice": "サボっちゃったんやね。疲れてたんかな？でも、ここでおしまいにするんはもったいないよ。1回休んでも大丈夫。明日からまたボチボチ始めよ？", "next_action_advice": "今日はゆっくりお風呂に入って寝て、明日はPCの電源を入れるところから始めよっか。"},
        {"fortune": "凶", "katsu": "もう、めっ！だよ？反省してね？🥺", "advice": "あちゃー、未達成マークがついちゃった。キミの目標、ここで諦めたらもったいないで！うち、キミが頑張る姿が一番好きなんやから、明日は一緒にがんばろう？", "next_action_advice": "明日やることを1つだけ決めて、アラームをかけておこなぁ。"}
    ]
    MIO_ENCOURAGE = [
        {"fortune": "吉", "katsu": "ええ調子やね、その調子や！🌻", "advice": "今日もコツコツ進められて偉いなぁ。完璧じゃなくてもいいから、ゆっくりキミのペースで続けていこな。うちがずっと隣で見守ってるからね。", "next_action_advice": "明日はほんの少し、5分だけでもいいから触ってみるようにしよなぁ。"},
        {"fortune": "小吉", "katsu": "一歩一歩、一緒に歩んでいこ♪🍀", "advice": "うんうん、ええ感じ！焦らんと、お茶でも飲みながらのんびり行こか。続けることが一番の近道なんやから、今日もハナマルやね！", "next_action_advice": "明日やることの準備（ノートを机に開く等）だけ、今やっておこか！"}
    ]
    MIO_TOTAL_REVIEW_HIGH = [
        {"fortune": "大吉", "katsu": "完走おめでとう！キミはほんまに最高の努力家や！🌸", "advice": "設定した期間、最後の1日までちゃんと記録できたね！しかも達成率80%以上なんて、ほんまにすごすぎるわぁ！キミがコツコツ頑張る姿、一番近くで見守れてうちは幸せやで。今日は美味しいものでも食べて、ゆっくり休んでね！", "next_action_advice": "次はどんな楽しい目標にしようか？少し休んだら、また一緒に新しい一歩を踏み出そうな♪"}
    ]
    MIO_TOTAL_REVIEW_LOW = [
        {"fortune": "末吉", "katsu": "最後までよう頑張ったね。お疲れ様やで！🍵", "advice": "チャレンジ期間が終わったね！達成率は80%に届かへんかったけど、途中で諦めんと、最後まで毎日記録をつけ続けたことが一番大きな一歩やで。その粘り強さがあれば、次はもっと上手くいくはずや！うちが保証するで♪", "next_action_advice": "まずは頑張った自分を労って、温かいお茶でも飲んでゆっくりしてな。次もまた一緒に頑張ろ？"}
    ]

    def __init__(self):
        self.llm_client = LLMClient()
        self.fortunes = ["大吉", "中吉", "小吉", "吉", "末吉", "凶"]

    def _analyze_progress(self, records: List[DailyRecordEntity]) -> Tuple[str, int]:
        """
        トラッカーの記録から、最大連続達成日数と最新の入力状態を解析します。
        """
        if not records:
            return "pending", 0
            
        sorted_records = sorted(records, key=lambda r: r.day_number)
        
        max_consecutive = 0
        current_consecutive = 0
        
        for r in sorted_records:
            if r.status == "achieved":
                current_consecutive += 1
                if current_consecutive > max_consecutive:
                    max_consecutive = current_consecutive
            else:
                current_consecutive = 0
                
        non_pending_records = [r for r in sorted_records if r.status != "pending"]
        if non_pending_records:
            latest_status = non_pending_records[-1].status
        else:
            latest_status = "pending"
            
        return latest_status, max_consecutive

    def generate_habit_feedback(
        self,
        tracker_title: str,
        period_days: int,
        records: List[DailyRecordEntity],
        character: str
    ) -> Tuple[str, str]:
        # 進捗を分析
        latest_status, max_consecutive = self._analyze_progress(records)
        
        # 完了判定（すべての入力が終わったか：pending のレコードが0）
        pending_count = sum(1 for r in records if r.status == "pending")
        is_completed = (pending_count == 0)
        
        # カテゴリ判定
        if is_completed:
            category = "total_review"
        elif latest_status == "slacked":
            category = "scold"
        elif max_consecutive >= 5:
            category = "praise"
        else:
            category = "encourage"

        try:
            # 履歴情報の文字列化
            history_str = ""
            for r in sorted(records, key=lambda x: x.day_number):
                status_ja = "達成" if r.status == "achieved" else "サボり" if r.status == "slacked" else "未入力"
                history_str += f"  - {r.day_number}日目: {status_ja}\n"

            # キャラクター別システムプロンプトの読み込み
            system_instruction = None
            db = SessionLocal()
            try:
                char_db = db.query(CharacterDB).filter(CharacterDB.id == character).first()
                if char_db:
                    system_instruction = f"{char_db.system_prompt}\n\n{COMMON_JSON_FORMAT}"
            except Exception as db_err:
                logger.error(f"Error fetching character prompt from DB: {db_err}")
            finally:
                db.close()

            if not system_instruction:
                system_instruction = SYSTEM_PROMPTS.get(character, SYSTEM_PROMPTS["ogami"])

            # ユーザープロンプトの設定
            if category == "total_review":
                achieved_count = sum(1 for r in records if r.status == "achieved")
                achievement_rate = round((achieved_count / len(records)) * 100) if records else 0
                user_prompt = (
                    f"【習慣習慣チャレンジ 最終結果】\n"
                    f"・習慣名: {tracker_title}\n"
                    f"・設定期間: {period_days}日間\n"
                    f"【最終進捗履歴】\n"
                    f"{history_str}"
                    f"・達成率: {achievement_rate}%\n"
                    f"・最大連続達成日数: {max_consecutive}日\n\n"
                    f"【命令】\n"
                    f"本日ですべての期間の入力が完了（チャレンジ終了）しました。これまでの取り組みに対する【最終総評】を行ってください。\n"
                    f"ユーザーの達成状況（達成率: {achievement_rate}%）に基づき、以下のトーンで総評してください。\n"
                    f"・達成率が80%以上の場合: キャラクターの個性を活かしつつ、全力で称賛し、大きな達成感を味わわせて次のステップを提示してください。\n"
                    f"・達成率が80%未満の場合: 最後まで記録を完了させたこと自体を労いつつ、今回の結果を反省させ、次回のチャレンジに繋がる愛のあるフィードバックを行ってください。\n\n"
                    f"必ず指示されたJSONフォーマットのみを出力し、説明文は一切含めないでください。"
                )
            else:
                user_prompt = (
                    f"【習慣チャレンジ情報】\n"
                    f"・習慣名: {tracker_title}\n"
                    f"・設定期間: {period_days}日間\n"
                    f"【現在の進捗履歴】\n"
                    f"{history_str}"
                    f"・最大連続達成日数: {max_consecutive}日\n"
                    f"・直近のアクション: {'サボってしまった(未達成)' if latest_status == 'slacked' else '達成した' if latest_status == 'achieved' else '未入力'}\n\n"
                    f"【命令】\n"
                    f"ユーザーの現在の状況（判定カテゴリ: '{category}'）に応じたフィードバックを行ってください。\n"
                    f"・'scold'の場合: 厳しく叱り、奮起させる内容（mioの場合は心配したしたしなめ方）\n"
                    f"・'praise'の場合: 5日連続達成を盛大に称賛・大絶賛する内容\n"
                    f"・'encourage'の場合: 継続を称え、温かく標準的に励ます内容\n\n"
                    f"必ず指示されたJSONフォーマットのみを出力し、説明文は一切含めないでください。"
                )

            # LLM呼び出し
            json_response = self.llm_client.generate_json_response(system_instruction, user_prompt)
            
            # 必要なキーの保証
            required_keys = ["fortune", "katsu", "advice", "next_action_advice"]
            for key in required_keys:
                if key not in json_response:
                    json_response[key] = ""
            
            return json.dumps(json_response, ensure_ascii=False), category

        except Exception as e:
            logger.error(f"Habit Tracker LLM Generation error (falling back to rule-based): {str(e)}")

        # --- ルールベースのフォールバック ---
        achieved_count = sum(1 for r in records if r.status == "achieved")
        achievement_rate = round((achieved_count / len(records)) * 100) if records else 0
        is_high_achievement = (achievement_rate >= 80)

        if character == "mio":
            if category == "total_review":
                fallback_data = random.choice(self.MIO_TOTAL_REVIEW_HIGH) if is_high_achievement else random.choice(self.MIO_TOTAL_REVIEW_LOW)
            elif category == "scold":
                fallback_data = random.choice(self.MIO_SCOLD)
            elif category == "praise":
                fallback_data = random.choice(self.MIO_PRAISE)
            else:
                fallback_data = random.choice(self.MIO_ENCOURAGE)
        else:  # ogami
            if category == "total_review":
                fallback_data = random.choice(self.OGAMI_TOTAL_REVIEW_HIGH) if is_high_achievement else random.choice(self.OGAMI_TOTAL_REVIEW_LOW)
            elif category == "scold":
                fallback_data = random.choice(self.OGAMI_SCOLD)
            elif category == "praise":
                fallback_data = random.choice(self.OGAMI_PRAISE)
            else:
                fallback_data = random.choice(self.OGAMI_ENCOURAGE)

        return json.dumps(fallback_data, ensure_ascii=False), category

    def generate_omikuji_feedback(
        self,
        character_id: str,
        consecutive_days: int,
        followed_plan: bool,
        user_message: str,
        history: List[HistoryEntity]
    ) -> Tuple[str, str, str, str]:
        # システムプロンプトの取得
        system_instruction = None
        db = SessionLocal()
        try:
            char_db = db.query(CharacterDB).filter(CharacterDB.id == character_id).first()
            if char_db:
                system_instruction = f"{char_db.system_prompt}\n\n{COMMON_JSON_FORMAT}"
        except Exception as db_err:
            logger.error(f"Error fetching character prompt from DB: {db_err}")
        finally:
            db.close()

        if not system_instruction:
            system_instruction = SYSTEM_PROMPTS.get(character_id, SYSTEM_PROMPTS["ogami"])

        # ユーザープロンプトの構築
        prompt = "【過去のやり取り】\n"
        if history:
            for h in history:
                prompt += f"- {h.timestamp.strftime('%Y-%m-%d')}: {h.user_message} (結果: {h.fortune}, アドバイス: {h.advice[:100]}...)\n"
        else:
            prompt += "なし\n"
            
        prompt += f"\n【現在の状況】\n"
        prompt += f"- 連続継続日数：{consecutive_days}日\n"
        prompt += f"- 計画の達成状況：{'計画通り進められた' if followed_plan else '計画通り進められなかった'}\n"
        prompt += f"- ユーザーの一言：『{user_message}』\n\n"
        
        prompt += "【指示】\n"
        prompt += "過去のやり取りを踏まえ、ユーザーの傾向（サボりがち、継続できている等）を把握した上でアドバイスを行ってください。\n"
        
        if character_id == "mio":
            if not followed_plan:
                prompt += "・計画通りに進められなかったみたい。お姉さんとして優しく、でも少し寂しそうに叱ってあげて。\n"
            if consecutive_days >= 7:
                prompt += f"・{consecutive_days}日も続いてるなんて、自分のことのように喜んで褒めちぎってあげて。\n"
            prompt += "・ミオとして、計画に対するおみくじの結果をJSONで返してね。"
        else:
            if not followed_plan:
                prompt += "・計画をサボっている。冒頭で厳しく叱責せよ。\n"
            if consecutive_days >= 7:
                prompt += f"・{consecutive_days}日も続いていることは、少しだけ（ツンデレ気味に）認めてやれ。\n"
            prompt += "・大神様として、計画に対するおみくじの結果をJSONで返せ。"

        try:
            # LLM呼び出し
            json_response = self.llm_client.generate_json_response(system_instruction, prompt)
            
            fortune = json_response.get("fortune", random.choice(self.fortunes))
            katsu = json_response.get("katsu", "喝！" if character_id == "ogami" else "あらあら")
            advice = json_response.get("advice", "精進せよ。" if character_id == "ogami" else "無理しないでね。")
            next_action_advice = json_response.get("next_action_advice", "まずは机に向かうのだ。" if character_id == "ogami" else "ゆっくり準備しようね。")
            
            return fortune, katsu, advice, next_action_advice

        except Exception as e:
            logger.error(f"Omikuji LLM Generation error (falling back to rule-based): {str(e)}")

        # --- ルールベースのフォールバック ---
        fortune = random.choice(self.fortunes)
        if character_id == "mio":
            katsu = "あらあら"
            advice = "無理しないでね。ボチボチいこな。"
            next_action_advice = "ゆっくり準備しようね。"
        else:
            katsu = "喝！"
            advice = "精進せよ。甘えを捨てよ。"
            next_action_advice = "まずは机に向かうのだ。"

        return fortune, katsu, advice, next_action_advice
