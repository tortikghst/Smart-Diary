import json
import httpx
from scr.config import settings

class YandexGPTService:
    @staticmethod
    async def generate_questions_from_ai(
        topic: str, subject_name: str = "Общий предмет", count: int = 2, q_type: str | None = None
    ) -> list[dict] | None:
        url = "https://caila.io/api/providers/openrouter/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
            "X-Mlp-Provider": "openrouter",
        }

        if q_type in ("choice", "single_choice", "multiple_choice", "match"):
            type_instruction = "Сгенерируй все вопросы строго с типом 'choice' (выбор ответа)."
        elif q_type in ("numeric", "math", "text_input"):
            type_instruction = "Сгенерируй все вопросы строго с типом 'numeric' (ввод числа)."
        else:
            type_instruction = "Сгенерируй вопросы разных типов: 'choice' и 'numeric'."

        # 🔥 ЧИСТЫЙ ПРОМПТ 🔥
        system_prompt = (
            f"Ты — эксперт по предмету '{subject_name}'. "
            f"Сгенерируй ровно {count} тестовых вопросов СТРОГО по теме: '{topic}'. "
            f"В поле 'question' напиши ТОЛЬКО текст самого вопроса. "
            f"НЕ пиши слова 'Тестовый вопрос', 'Вопрос', 'Тема', не повторяй название темы в тексте. "
            f"Категорически запрещено использовать термины и вопросы из других предметов. "
            f"{type_instruction} "
            f"Если type='choice': добавь 'options' (массив из 3 строк) и 'correct_option_index' (индекс от 0 до 2). "
            f"Если type='numeric': добавь 'numeric_answer' (число)."
        )

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Тема: {topic}"},
            ],
            "temperature": 0.2,  # Строго 0.2 для минимума фантазий
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "test_questions",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "question": {"type": "string"},
                                        "type": {"type": "string", "enum": ["choice", "numeric"]},
                                        "options": {"type": "array", "items": {"type": "string"}},
                                        "correct_option_index": {"type": "integer"},
                                        "numeric_answer": {"type": "number"},
                                    },
                                    "required": ["question", "type"],
                                    "additionalProperties": False,
                                },
                            }
                        },
                        "required": ["questions"],
                        "additionalProperties": False,
                    },
                },
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=40.0)
                if response.status_code != 200:
                    print(f"⚠️ Caila вернула статус {response.status_code}: {response.text}")
                    return None

                result = response.json()
                raw_text = result["choices"][0]["message"]["content"].strip()
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                
                data = json.loads(raw_text)
                return data.get("questions", [])
        except Exception as e:
            print(f"⚠️ Ошибка при запросе к Caila: {e}")
            return None
    @staticmethod
    async def generate_text(prompt: str) -> str | None:
        """
        Отправляет запрос в Caila для генерации обычного текста (без JSON).
        Используется для рекомендаций и объяснений.
        """
        url = "https://caila.io/api/providers/openrouter/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
            "X-Mlp-Provider": "openrouter",
        }

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "Ты — полезный школьный ИИ-ассистент. Отвечай кратко, понятно и только по делу. Без лишних приветствий и форматирования."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                if response.status_code != 200:
                    print(f"⚠️ Caila (text) вернула статус {response.status_code}: {response.text}")
                    return None

                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ Ошибка при запросе текста к Caila: {e}")
            return None