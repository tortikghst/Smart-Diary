from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.services.jwt_service import JWTService
from scr.schemas.auth_schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)

auth = APIRouter(prefix="/auth", tags=["Авторизация"])


@auth.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,  # ИСПРАВЛЕНО: строго LoginRequest вместо EmailRequest
    db: AsyncSession = Depends(get_db_session),
):
    """
    Эндпоинт авторизации через мессенджер MAX (§9.3).
    Теперь Swagger и Pydantic работают на единой схеме LoginRequest.
    """
    init_data_string = payload.initData  # Логика чтения остается прежней

    # 1. Валидация подписи initData мессенджера MAX (§7.1)
    max_user_data = JWTService.validate_max_init_data(init_data_string)

    if not max_user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка валидации данных запуска MAX initData. Неверная подпись.",
        )

    # Извлечение vk_id из параметров платформы
    try:
        vk_id = int(max_user_data.get("id"))
        first_name = max_user_data.get("first_name", "Новый")
        last_name = max_user_data.get("last_name", "Пользователь")
        full_name = f"{last_name} {first_name}".strip()
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В данных запуска отсутствует корректный цифровой VK ID",
        )

    # 2. Поиск или автоматическая регистрация по vk_id
    user = await UserRepository.get_user_by_vk_id(db=db, vk_id=vk_id)
    if not user:
        user = await UserRepository.create_pending_user(
            db=db, vk_id=vk_id, full_name=full_name
        )

    # 3. Контроль доступа для нераспределенных пользователей (§7.2)
    if user.role.value == "student" and user.class_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Регистрация успешна. Доступ ограничен до привязки к классу администратором.",
        )

    # 4. Сборка контекста классов для Payload JWT токена (§7.3)
    class_context = {}
    if user.role.value == "student":
        class_context = {"class_id": user.class_id}
    elif user.role.value == "teacher":
        teacher_classes = await UserRepository.get_teacher_classes(
            db=db, teacher_id=user.user_id
        )
        class_context = {"class_ids": [c.class_id for c in teacher_classes]}

    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)

    tokens = JWTService.generate_auth_tokens(
        user_id=user.user_id,
        role=user_role_str,  # СИНХРОНИЗАЦИЯ: передаем роль в сервис
        token_version=1,
    )

    return {
        "message": "Вход успешно выполнен",
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "user": user,
    }


@auth.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_tokens(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db_session)
):
    """Ротация токенов по refresh_token (§7.3)"""
    token_data = JWTService.verify_refresh_token(payload.refresh_token)
    user_id = token_data["user_id"]

    user = await UserRepository.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден"
        )

    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)

    new_tokens = JWTService.generate_auth_tokens(
        user_id=user.user_id,
        role=user_role_str,  # СИНХРОНИЗАЦИЯ: передаем роль в сервис
        token_version=token_data.get("version", 1),
    )

    return {
        "message": "Токены успешно обновлены",
        "access_token": new_tokens["access_token"],
        "refresh_token": new_tokens["refresh_token"],
        "token_type": new_tokens["token_type"],
    }
