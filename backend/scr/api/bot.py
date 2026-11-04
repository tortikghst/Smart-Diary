import httpx
from fastapi import APIRouter, Request, HTTPException
from scr.config import settings

bot_router = APIRouter(prefix="/bot", tags=["Бот MAX"])

# Сюда мы будем стучаться, чтобы отправить сообщение от бота
MAX_API_URL = "https://botapi.max.ru/messages"
MINI_APP_URL = "https://твой-фронтенд-урл.com" # <--- ТУТ БУДЕТ ССЫЛКА НА ТВОЙ ФРОНТЕНД


@bot_router.post("/webhook")
async def max_bot_webhook(request: Request):
    """
    Вебхук для получения обновлений от MAX.
    Когда пользователь пишет боту /start, мы отправляем ему "лендинг" с кнопкой.
    """
    data = await request.json()
    
    # 1. Проверяем, что это сообщение (а не какое-то системное событие)
    update_type = data.get("update_type")
    if update_type != "message_created":
        return {"ok": True}
        
    message = data.get("message", {})
    text = message.get("body", {}).get("text", "").strip()
    chat_id = message.get("recipient", {}).get("chat_id")
    user_id = message.get("sender", {}).get("user_id")

    # 2. Если пользователь нажал "Старт" или написал /start
    if text.startswith("/start") or text.lower() in ("привет", "start"):
        
        # Формируем красивое сообщение (лендинг) с кнопкой
        payload = {
            "chat_id": chat_id,
            "text": "👋 Добро пожаловать в Умный дневник!\n\n"
                    "Здесь вы можете смотреть оценки, проверять долги и проходить ИИ-тесты.\n"
                    "Нажмите на кнопку ниже, чтобы открыть приложение.",
            "attachments": [
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "buttons": [
                            [
                                {
                                    "type": "link",
                                    "text": "🚀 Открыть Дневник",
                                    "url": MINI_APP_URL
                                }
                            ]
                        ]
                    }
                }
            ]
        }

        # 3. Отправляем запрос в API MAX
        headers = {
            "Authorization": f"Bearer {settings.MAX_BOT_TOKEN}" # <--- Токен бота в .env
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(MAX_API_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Ошибка отправки сообщения MAX: {response.text}")
                return {"ok": False}
                
    return {"ok": True}