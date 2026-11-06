import json
import httpx
import traceback
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
            "HTTP-Referer": "https://smart-diary.ru",
            "X-Title": "Smart Diary"
        }

        if q_type in ("choice", "single_choice", "multiple_choice", "match"):
            type_instruction = "Сгенерируй все вопросы строго с типом 'choice' (выбор ответа)."
        elif q_type in ("numeric", "math", "text_input"):
            type_instruction = "Сгенерируй все вопросы строго с типом 'numeric' (ввод числа)."
        else:
            type_instruction = "Сгенерируй вопросы разных типов: 'choice' и 'numeric'."

        system_prompt = (
            f"Ты — опытный школьный методист, эксперт по ФГОС РФ. "
            f"Твоя задача — составить проверочную работу по предмету '{subject_name}' на тему '{topic}' для учеников средней школы. "
            f"Сгенерируй ровно {count} вопросов. "
            f"Вопросы должны строго соответствовать школьной программе РФ и возрастным особенностям учеников. "
            f"Категорически запрещено использовать термины и концепции из других предметов. "
            f"В поле 'question' напиши ТОЛЬКО текст вопроса. Не пиши слова 'Тестовый вопрос', 'Вопрос', не повторяй тему. "
            f"{type_instruction} "
            f"Если type='choice': добавь 'options' (массив ровно из 3 строк) и 'correct_option_index' (индекс от 0 до 2). "
            f"Если type='numeric': добавь 'numeric_answer' (число). "
            f"Верни ответ строго в формате JSON без markdown-разметки."
        )

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Тема: {topic}. Предмет: {subject_name}"},
            ],
            "temperature": 0.2,
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
                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                
                if response.status_code != 200:
                    print(f"🚨🚨🚨 CAILA СТАТУС: {response.status_code}", flush=True)
                    print(f"🚨🚨🚨 ОТВЕТ: {response.text}", flush=True)
                    return None

                result = response.json()
                raw_text = result["choices"][0]["message"]["content"].strip()
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                
                data = json.loads(raw_text)
                return data.get("questions", [])
                
        except Exception as e:
            print(f"🚨🚨🚨 ОШИБКА В LLM_SERVICE: {repr(e)}", flush=True)
            traceback.print_exc()
            return None

    @staticmethod
    async def generate_text(prompt: str) -> str | None:
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
                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                if response.status_code != 200:
                    print(f"🚨🚨🚨 CAILA (TEXT) СТАТУС: {response.status_code}", flush=True)
                    print(f"🚨🚨🚨 ОТВЕТ: {response.text}", flush=True)
                    return None

                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"🚨🚨🚨 ОШИБКА ПРИ ЗАПРОСЕ ТЕКСТА: {repr(e)}", flush=True)
            traceback.print_exc()
            return None
