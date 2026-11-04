import sys
import json
import datetime


class StructuredLogger:
    @staticmethod
    def log(
        level: str,
        event: str,
        context: dict | None = None,
        request_id: str | None = None,
        user_id: int | None = None,
    ) -> None:
        """
        Выводит структурированный лог в формат JSON Lines (§13.5).
        Запрещено выводить full_name/ФИО в stdout. Стираем при наличии.
        """
        ctx = context.copy() if context else {}

        # Жесткая очистка от ПДн для stdout безопасности (§13.5)
        if "full_name" in ctx:
            ctx.pop("full_name")
        if "fio" in ctx:
            ctx.pop("fio")

        log_payload = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
            "level": level.lower(),
            "logger": "app.structured_log",
            "event": event,
            "request_id": request_id,
            "user_id": user_id,
            "context": ctx,
        }

        # Пишем в stdout атомарной строкой JSON Lines
        sys.stdout.write(json.dumps(log_payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
