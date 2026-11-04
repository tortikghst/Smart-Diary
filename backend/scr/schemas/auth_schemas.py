from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# --- Схемы Запросов (Request Body) ---


class EmailRequest(BaseModel):
    """Схема для запроса отправки OTP-кода"""

    email: EmailStr


class VerifyRequest(BaseModel):
    """Схема для проверки OTP-кода"""

    email: EmailStr
    code: str


class LoginRequest(BaseModel):
    """Строгий контракт запроса авторизации согласно §9.3 ТЗ"""

    initData: str = Field(
        ..., description="Подписанная строка данных запуска из MAX Bridge"
    )


class RefreshRequest(BaseModel):
    refresh_token: str


class UserSchema(BaseModel):
    user_id: int
    full_name: str
    role: str
    class_id: Optional[int] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    user: UserSchema
