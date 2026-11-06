from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import time
from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.api.auth_deps import require_role
from scr.schemas.journal_schemas import ClassStudentSchema, FullJournalResponse
from datetime import date, timedelta
from scr.schemas.analytics_schemas import ClassAnalyticsResponse
from scr.api.auth_deps_own import check_class_owner

journal_router = APIRouter(prefix="/classes", tags=["Электронный Журнал"])

# 🔥 Глобальные кэши в памяти 🔥
_analytics_cache = {}  # ключ -> (timestamp, data)
_ai_cache = {}         # ключ -> (timestamp, ai_text)
CACHE_TTL = 300        # 5 минут (для аналитики)
AI_CACHE_TTL = 600     # 10 минут (для ИИ, он генерируется дольше)

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
    subject_id: int = Query(..., description="ID предмета (например, 3 для Математики)"),
    page: int = Query(1, ge=1, description="Номер страницы пагинации (§9.1)"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы (§9.1)"),
    current_user: dict = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
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
    date_from: Optional[date] = Query(None, description="Начало периода"),
    date_to: Optional[date] = Query(None, description="Конец периода"),
    current_user: dict = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
    teacher_id = int(current_user["sub"])

    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    # 🔥 КЭШИРОВАНИЕ БЫСТРОЙ АНАЛИТИКИ 🔥
    cache_key = f"analytics_{teacher_id}_{class_id}_{date_from}_{date_to}"
    now = time.time()

    if cache_key in _analytics_cache:
        cached_time, cached_data = _analytics_cache[cache_key]
        if now - cached_time < CACHE_TTL:
            print(f"📦 [ANALYTICS-CACHE] Отдаем быструю аналитику из кэша для класса {class_id}")
            return cached_data

    analytics_data = await UserRepository.get_class_analytics_data(
        db=db, class_id=class_id, teacher_id=teacher_id, date_from=date_from, date_to=date_to,
    )

    if not analytics_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не удалось собрать аналитику. Проверьте, закреплен ли за вами этот класс.",
        )

    _analytics_cache[cache_key] = (now, analytics_data)
    return analytics_data


@journal_router.get(
    "/{class_id}/analytics/recommendation",
    status_code=status.HTTP_200_OK,
)
async def get_class_ai_recommendation(
    class_id: int,
    _: None = Depends(check_class_owner),
    current_user: dict = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
    teacher_id = int(current_user["sub"])
    date_to = date.today()
    date_from = date_to - timedelta(days=30)

    # 🔥 КЭШИРОВАНИЕ РЕКОМЕНДАЦИИ ИИ 🔥
    cache_key = f"ai_rec_{teacher_id}_{class_id}"
    now = time.time()

    if cache_key in _ai_cache:
        cached_time, cached_text = _ai_cache[cache_key]
        if now - cached_time < AI_CACHE_TTL:
            print(f"📦 [AI-CACHE] Отдаем рекомендацию ИИ из кэша для класса {class_id}")
            return {"ai_recommendation": cached_text}

    # Если в кэше нет — генерируем (это займет время)
    recommendation = await UserRepository.generate_ai_recommendation(
        db=db, class_id=class_id, teacher_id=teacher_id, date_from=date_from, date_to=date_to
    )

    # Сохраняем в кэш, даже если ИИ вернул None (чтобы не спамить запросами при ошибке)
    _ai_cache[cache_key] = (now, recommendation)
    
    return {"ai_recommendation": recommendation}
