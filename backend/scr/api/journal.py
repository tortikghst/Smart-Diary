from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.api.auth_deps import require_role
from scr.schemas.journal_schemas import ClassStudentSchema, FullJournalResponse
from datetime import date, timedelta
from scr.schemas.analytics_schemas import ClassAnalyticsResponse
from scr.api.auth_deps_own import check_class_owner

journal_router = APIRouter(prefix="/classes", tags=["Электронный Журнал"])


@journal_router.get(
    "/{class_id}/students",
    response_model=list[ClassStudentSchema],
    status_code=status.HTTP_200_OK,
)
async def get_students(
    class_id: int,
    _: None = Depends(check_class_owner),
    current_user: dict = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получить список всех учеников класса для отрисовки сетки рассадки и журнала (Страница 6 Контракта).
    """
    students = await UserRepository.get_class_students(db=db, class_id=class_id)
    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="В данном классе не найдено зарегистрированных учеников.",
        )
    return students


@journal_router.get(
    "/{class_id}/journal",
    response_model=FullJournalResponse,
    status_code=status.HTTP_200_OK,
)
async def get_journal(
    class_id: int,
    _: None = Depends(check_class_owner),
    subject_id: int = Query(
        ..., description="ID предмета (например, 3 для Математики)"
    ),
    page: int = Query(1, ge=1, description="Номер страницы пагинации (§9.1)"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы (§9.1)"),
    current_user: dict = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Возвращает агрегированную сетку успеваемости класса: список учеников, уроки и total_pages (Страница 6 Контракта).
    """
    journal_data = await UserRepository.get_full_class_journal(
        db=db, class_id=class_id, subject_id=subject_id, page=page, page_size=page_size
    )
    return journal_data


@journal_router.get(
    "/{class_id}/analytics",
    response_model=ClassAnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_class_analytics(
    class_id: int,
    _: None = Depends(check_class_owner),
    date_from: Optional[date] = Query(
        None, description="Начало периода (по умолчанию -30 дней)"
    ),
    date_to: Optional[date] = Query(
        None, description="Конец периода (по умолчанию сегодня)"
    ),
    current_user: dict = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получить аналитику успеваемости класса («Портрет класса» и «Карта пробелов») (Страница 5 Контракта).
    Вычисляет распределение оценок, средние показатели по темам и самую слабую зону класса.
    """
    teacher_id = int(current_user["sub"])

    # Выставляем дефолтные 30 дней, если параметры не переданы фронтендом (Страница 5 Контракта)
    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    analytics_data = await UserRepository.get_class_analytics_data(
        db=db,
        class_id=class_id,
        teacher_id=teacher_id,
        date_from=date_from,
        date_to=date_to,
    )

    if not analytics_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не удалось собрать аналитику. Проверьте, закреплен ли за вами этот класс.",
        )

    return analytics_data
