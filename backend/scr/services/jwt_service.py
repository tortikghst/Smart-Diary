from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, status
from scr.config import settings
import hmac
import hashlib
import urllib.parse
import json


class JWTService:
    @staticmethod
    def create_token(payload_data: dict, expires_delta: timedelta) -> str:
        """Внутренний метод для сборки токена"""
        payload = payload_data.copy()
        payload.update({"exp": datetime.now(timezone.utc) + expires_delta})
        return jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    @classmethod
    def generate_auth_tokens(cls, user_id: int, role: str, token_version: int) -> dict:
        """
        ИСПРАВЛЕНО: Добавлен аргумент role в сигнатуру метода!
        Генерирует пару токенов (Access + Refresh) с сохранением роли в payload токена (§7.3 ТЗ).
        """
        access_payload = {
            "sub": str(user_id),
            "role": str(
                role
            ),  # Теперь переменная 'role' легитимна и берется из аргументов
            "type": "access",
        }
        access_token = cls.create_token(
            access_payload, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        refresh_payload = {
            "sub": str(user_id),
            "version": token_version,
            "type": "refresh",
        }
        refresh_token = cls.create_token(
            refresh_payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def verify_access_token(token: str) -> dict:
        """
        ИСПРАВЛЕНО: Теперь метод возвращает полный словарь (payload), а не число!
        Дешифрует Access токен и валидирует его структуру для слоя зависимостей.
        """
        try:
            from jose import jwt, JWTError, ExpiredSignatureError
            from fastapi import HTTPException, status

            # Декодируем токен с использованием вашего секретного ключа
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )

            # Проверяем наличие обязательного поля 'sub' (идентификатор пользователя)
            if payload.get("sub") is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="В токене отсутствует обязательный идентификатор пользователя (sub)",
                )

            # СТРОГИЙ РЕЖИМ: Возвращаем СЛОВАРЬ целиком, содержащий и sub, и роль!
            return payload

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Срок действия Access token истек",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный access token",
            )

    @staticmethod
    def verify_refresh_token(token: str) -> dict:
        """Дешифрует и проверяет Refresh токен для эндпоинта обновления токенов"""
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )

            # Проверяем тип токена
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Неверный тип токена. Ожидается refresh_token",
                )

            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="В токен-обновлении отсутствует ID пользователя",
                )
            return {"user_id": int(user_id), "version": payload.get("version", 1)}

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired. Пожалуйста, войдите заново",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

    @staticmethod
    def validate_max_init_data(init_data: str) -> dict | None:
        """
        Проверяет подпись строки window.WebApp.initData по официальному гайду MAX (§7.1 ТЗ).
        Для хакатона поддерживает мгновенный бесшовный вход демо-пользователей.
        """
        try:
            # СТРОГО ПО КОНТРАКТУ v0.2 (Страница 4): Проверка на демо-вход судей/разработчиков
            # Имена (first_name, last_name) должны строго соответствовать ФИО в seed_demo_data
            if "teacher" in init_data:
                return {"id": 12345, "first_name": "Марина", "last_name": "Соколова"}
            if "student" in init_data:
                return {"id": 23456, "first_name": "Иван", "last_name": "Иванов"}

            # 1. Декодируем query-строку параметров для реального входа из мессенджера
            parsed_data = dict(
                urllib.parse.parse_qsl(init_data, keep_blank_values=True)
            )

            # Если хэша нет и это не демо-строка, то данные некорректны
            if "hash" not in parsed_data:
                return None

            received_hash = parsed_data.pop("hash")

            # 2. Сортируем параметры по алфавиту
            sorted_items = sorted(parsed_data.items())
            data_check_string = "\n".join([f"{k}={v}" for k, v in sorted_items])

            # 3. Вычисляем секретный ключ на основе токена вашего бота
            bot_token = getattr(settings, "MAX_BOT_TOKEN", "mock_bot_token")
            secret_key = hmac.new(
                b"WebAppsData", bot_token.encode(), hashlib.sha256
            ).digest()

            # 4. Считаем проверочный хэш
            computed_hash = hmac.new(
                secret_key, data_check_string.encode(), hashlib.sha256
            ).hexdigest()

            # Если подпись совпала, парсим встроенный JSON-объект user
            if hmac.compare_digest(computed_hash, received_hash):
                user_json = parsed_data.get("user")
                if user_json:
                    return json.loads(user_json)
                return parsed_data

            return None
        except Exception:
            return None
