from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.api.auth_deps import require_role
from scr.schemas.user_schemas import UserMeResponse

users_router = APIRouter(prefix="/users", tags=["Пользователи"])


@users_router.get("/me", response_model=UserMeResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: dict = Depends(require_role(["student", "teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Защищенный эндпоинт профиля текущего пользователя (§9.3).
    Строго возвращает subject для учителя под требования шапки фронтенда.
    """
    user_id = int(current_user["sub"])

    # Запрашиваем очищенные данные через репозиторий
    profile_data = await UserRepository.get_user_profile_with_subject(
        db=db, user_id=user_id
    )

    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль авторизованного пользователя не найден в базе данных.",
        )

    return profile_data
