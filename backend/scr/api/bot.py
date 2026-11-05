import httpx
from fastapi import APIRouter, Request, HTTPException
from scr.config import settings


bot_router = APIRouter(tags=["Бот MAX"])

# Куда отправлять сообщения
MAX_API_URL = "https://botapi.max.ru/messages"

# Ссылка на фронтенд (для кнопки в боте)
MINI_APP_URL = "https://sovolud.ru"


@bot_router.post("/webhook")
async def max_bot_webhook(request: Request):
    """
    Вебхук для получения обновлений от MAX.

    MAX присылает разные форматы:
      - bot_started:     { update_type, chat_id, user: { user_id, ... }, timestamp }
      - message_created: { update_type, message: { body: {text}, recipient: {chat_id}, sender: {user_id} }, ... }
    Обрабатываем оба.
    """
    data = await request.json()
    print(f"📩 [MAX-WEBHOOK] raw data: {data}")

    update_type = data.get("update_type")
    if update_type not in ("message_created", "bot_started"):
        print(f"⏭️  [MAX-WEBHOOK] skip update_type={update_type}")
        return {"ok": True}

    # --- Разбор разных форматов ---
    chat_id = data.get("chat_id")
    text = ""
    user_id = None

    if chat_id is not None:
        # формат bot_started
        user = data.get("user") or {}
        user_id = user.get("user_id")
    else:
        # формат message_created
        message = data.get("message") or {}
        text = ((message.get("body") or {}).get("text") or "").strip()
        chat_id = (message.get("recipient") or {}).get("chat_id")
        user_id = (message.get("sender") or {}).get("user_id")

    print(
        f"📩 [MAX-WEBHOOK] type={update_type}, text={text!r}, "
        f"chat_id={chat_id}, user_id={user_id}"
    )

    # --- Отвечаем на bot_started и на /start (или "привет"/"start") ---
    is_start = (
        update_type == "bot_started"
        or text.startswith("/start")
        or text.lower() in ("привет", "start")
    )
    if not is_start:
        return {"ok": True}

    payload = {
        "text": (
            "👋 Добро пожаловать в Умный дневник!\n\n"
            "Здесь вы можете смотреть оценки, проверять долги и проходить ИИ-тесты.\n"
            "Нажмите на кнопку ниже, чтобы открыть приложение."
        ),
        "attachments": [
            {
                "type": "inline_keyboard",
                "payload": {
                    "buttons": [
                        [
                            {
                                "type": "link",
                                "text": "🚀 Открыть Дневник",
                                "url": MINI_APP_URL,
                            }
                        ]
                    ]
                },
            }
        ],
    }

    # --- chat_id / user_id идут В QUERY, токен — в заголовке Authorization (БЕЗ "Bearer") ---
    params = {}
    if chat_id:
        params["chat_id"] = chat_id
    elif user_id:
        params["user_id"] = user_id
    else:
        print("❌ [MAX-WEBHOOK] нет ни chat_id, ни user_id — некуда отвечать")
        return {"ok": False}

    headers = {"Authorization": settings.MAX_BOT_TOKEN}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            MAX_API_URL, params=params, json=payload, headers=headers
        )
        print(f"📤 [MAX-WEBHOOK] MAX response: {response.status_code} {response.text}")
        if response.status_code != 200:
            return {"ok": False}

    return {"ok": True}
