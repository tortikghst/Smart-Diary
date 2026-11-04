from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from scr.services.jwt_service import JWTService

security = HTTPBearer()


async def get_current_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Возвращает полный payload словарь токена."""
    token = credentials.credentials
    payload = JWTService.verify_access_token(token)
    return payload


async def get_current_user_id(
    token_data: dict = Depends(get_current_token_data),
) -> int:
    """Безопасно извлекает sub из словаря token_data."""
    return int(token_data["sub"])


def require_role(allowed_roles: list[str]):
    """Фабрика проверки матрицы доступа."""

    async def role_dependency(
        token_data: dict = Depends(get_current_token_data),
    ) -> dict:
        user_role = token_data.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Недостаточно прав для выполнения операции.",
            )
        return token_data

    return role_dependency
