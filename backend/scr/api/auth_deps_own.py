"""Проверка прав владения классом (D1)."""
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scr.database import get_db_session
from scr.api.auth_deps import get_current_token_data
from scr.model.model import ClassSubjectModel, UserModel


async def check_class_owner(
    class_id: int,
    current_user: dict = Depends(get_current_token_data),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Проверяет, что текущий пользователь — админ или учитель этого класса.
    """
    user_id = int(current_user["sub"])
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден.",
        )

    role = getattr(user.role, "value", user.role)
    if str(role) == "admin":
        return  # Админ видит всё

    if str(role) != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для учителей.",
        )

    stmt = (
        select(ClassSubjectModel)
        .where(
            ClassSubjectModel.class_id == class_id,
            ClassSubjectModel.teacher_id == user_id,
        )
        .limit(1)
    )
    owns = (await db.execute(stmt)).scalar_one_or_none()
    if not owns:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не ведёте предметы в этом классе.",
        )