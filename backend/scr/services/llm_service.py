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

        # 🔥 ОБНОВЛЕННЫЙ ПРОМПТ ДЛЯ ФГОС 🔥
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
        
        # ... далее код отправки запроса без изменений ...