import json
import logging
import time
import random
import openai
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # GEMINI_API_KEYが設定されていればそれを、設定されていなければローカルLLM用のデフォルト値を使用
        api_key = settings.GEMINI_API_KEY or "lm-studio"
        self.client = OpenAI(
            base_url=settings.LLM_API_BASE,
            api_key=api_key,
        )

    def generate_json_response(self, system_instruction: str, user_prompt: str) -> dict:
        max_retries = 5
        initial_delay = 2.0
        backoff_factor = 2.0

        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries + 1}): {user_prompt}")
                logger.debug(f"System instruction: {system_instruction}")

                response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                )

                raw_content = response.choices[0].message.content.strip()
                logger.info(f"Raw LLM response: {raw_content}")

                # Markdownのコードブロックが含まれている場合は除去
                if raw_content.startswith("```"):
                    # ```json や ``` の後の最初の { を探す
                    start = raw_content.find("{")
                    end = raw_content.rfind("}")
                    if start != -1 and end != -1:
                        raw_content = raw_content[start:end+1]

                # JSONとしてパース
                return json.loads(raw_content)

            except (openai.RateLimitError, openai.APIConnectionError) as e:
                if attempt == max_retries:
                    logger.error(f"LLM max retries ({max_retries}) reached. Error: {str(e)}")
                    raise e
                
                # 指数バックオフ + ジッター (0〜1秒のランダム値を追加)
                delay = initial_delay * (backoff_factor ** attempt) + random.uniform(0, 1.0)
                logger.warning(
                    f"LLM rate limit or connection error: {str(e)}. "
                    f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(delay)

            except Exception as e:
                logger.error(f"LLM Connection/Parsing Error: {str(e)}")
                raise e
