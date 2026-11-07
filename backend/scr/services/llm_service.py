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

        if q_type == "matching":
            type_instruction = "Сгенерируй все вопросы строго с типом 'matching' (сопоставление пар)."
        elif q_type in ("choice", "single_choice", "multiple_choice"):
            type_instruction = "Сгенерируй все вопросы строго с типом 'choice' (выбор ответа)."
        elif q_type in ("numeric", "math", "text_input"):
            type_instruction = "Сгенерируй все вопросы строго с типом 'numeric' (ввод числа)."
        else:
            type_instruction = (
                "Сгенерируй вопросы РАЗНЫХ типов: обязательно добавь 'choice' (тест), 'numeric' (число) "
                "и 'matching' (сопоставление). Распредели их равномерно."
            )

        system_prompt = (
            f"Ты — опытный школьный методист, эксперт по ФГОС РФ. "
            f"Твоя задача — составить проверочную работу по предмету '{subject_name}' на тему '{topic}' для учеников средней школы. "
            f"Сгенерируй ровно {count} вопросов. "
            f"Вопросы должны строго соответствовать школьной программе РФ и возрастным особенностям учеников. "
            f"Категорически запрещено использовать термины и концепции из других предметов. "
            f"В поле 'question' напиши ТОЛЬКО текст вопроса. Не пиши слова 'Тестовый вопрос', 'Вопрос', не повторяй тему. "
            f"{type_instruction} "
            f"ПРАВИЛА ФОРМАТИРОВАНИЯ: "
            f"1. Если type='choice': добавь 'options' (массив ровно из 3 строк) и 'correct_option_index' (индекс от 0 до 2). "
            f"2. Если type='numeric': добавь 'numeric_answer' (число). "
            f"3. Если type='matching': добавь 'left' (массив терминов слева) и 'right' (массив определений справа), "
            f"а также 'correct_matches' (объект, где ключи — элементы из left, а значения — правильные элементы из right). "
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
                                        "type": {"type": "string", "enum": ["choice", "numeric", "matching"]},
                                        "options": {"type": "array", "items": {"type": "string"}},
                                        "correct_option_index": {"type": "integer"},
                                        "numeric_answer": {"type": "number"},
                                        "left": {"type": "array", "items": {"type": "string"}},
                                        "right": {"type": "array", "items": {"type": "string"}},
                                        "correct_matches": {"type": "object", "additionalProperties": {"type": "string"}}
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
                choice = result.get("choices", [{}])[0]
                message = choice.get("message", {})
                
                data_list = []

                # 👇 1. ПРОВЕРЯЕМ TOOL_CALLS (как делает Llama 3.3) 👇
                if message.get("tool_calls"):
                    print("🤖 Модель вернула ответ через tool_calls, парсим...", flush=True)
                    args_str = message["tool_calls"][0]["function"]["arguments"]
                    parsed_args = json.loads(args_str)
                    
                    questions_obj = parsed_args.get("questions", [])
                    
                    # Llama иногда оборачивает массив в {"type": "array", "value": [...]}
                    if isinstance(questions_obj, dict) and "value" in questions_obj:
                        data_list = questions_obj["value"]
                    elif isinstance(questions_obj, list):
                        data_list = questions_obj
                        
                # 👇 2. ПРОВЕРЯЕМ CONTENT (как делают другие модели) 👇
                elif message.get("content"):
                    raw_text = message["content"].strip()
                    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                    parsed_json = json.loads(raw_text)
                    data_list = parsed_json.get("questions", [])
                
                if not data_list:
                    print(f"🚨🚨🚨 CAILA ВЕРНУЛА ПУСТОЙ ОТВЕТ. Полный ответ: {result}", flush=True)
                    return None

                return data_list
                
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
                message = result.get("choices", [{}])[0].get("message", {})
                return message.get("content", "").strip() if message.get("content") else None
                
        except Exception as e:
            print(f"🚨🚨🚨 ОШИБКА ПРИ ЗАПРОСЕ ТЕКСТА: {repr(e)}", flush=True)
            traceback.print_exc()
            return None
