from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.api.auth_deps import require_role
from scr.schemas.streak_schemas import StudentStreakResponse
from scr.schemas.debt_schemas import StudentDebtResponse
from scr.schemas.student_dashboard_schemas import StudentDashboardResponse
from scr.schemas.student_grades_schemas import StudentSubjectGradesResponse
from scr.schemas.rating_schemas import StudentRatingResponse
from scr.schemas.mascot_schemas import MascotResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from scr.model.model import (
    DebtModel,
    LessonModel,
    PlanTopicModel,
    TestModel,
    StudyPlanModel,
)
from scr.schemas.test_schemas import PrepTestResponse

student_router = APIRouter(prefix="/student", tags=["Панель Ученика"])


@student_router.get(
    "/rating", response_model=StudentRatingResponse, status_code=status.HTTP_200_OK
)
async def get_student_rating(
    type: str = Query(
        ...,
        description="Тип рейтинга: exam (экзамены) или vpr (ВПР) (Страница 10 Контракта)",
    ),
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получение рейтинга классов параллели по экзаменам или ВПР для дашборда ученика (Страница 10 Контракта).
    Использует JWT токен для определения параллели и автоматической подсветки класса (my_class_id).
    """
    student_id = int(current_user["sub"])

    # Передаем id текущего пользователя и тип события в репозиторий
    rating_data = await UserRepository.get_parallel_rating(
        db=db, student_id=student_id, event_type=type
    )

    if not rating_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось загрузить рейтинг. Проверьте валидность параметра type или привязку профиля к классу.",
        )

    return rating_data


@student_router.get(
    "/grades",
    response_model=StudentSubjectGradesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_grades(
    subject_id: int = Query(
        ..., description="ID предмета для фильтрации отчёта (Страница 9 Контракта)"
    ),
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получение личного журнала («Отчёт по предмету») авторизованного ученика (Страница 9 Контракта).
    Фильтрует оценки по предмету, рассчитывает средний балл и процент успеваемости по ДЗ.
    """
    user_id = int(current_user["sub"])

    # Запрашиваем отфильтрованную структуру у репозитория
    grades_data = await UserRepository.get_filtered_student_grades(
        db=db, student_id=user_id, subject_id=subject_id
    )

    if not grades_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запрашиваемый предмет не найден в системе.",
        )

    return grades_data


@student_router.get(
    "/dashboard",
    response_model=StudentDashboardResponse,
    status_code=status.HTTP_200_OK,
)
async def get_student_dashboard(
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получение агрегированных данных главного экрана ученика (Страница 9 Контракта).
    Отдает список предметов, лучший текущий стрик («Огонёк»), число долгов и список ИИ-тестов.
    """
    student_id = int(current_user["sub"])

    # Запрашиваем собранный дашборд у репозитория
    dashboard_data = await UserRepository.get_student_dashboard_data(
        db=db, student_id=student_id
    )
    return dashboard_data


@student_router.get(
    "/streaks",
    response_model=list[StudentStreakResponse],
    status_code=status.HTTP_200_OK,
)
async def get_streaks(
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получение всех огней (серий ДЗ) текущего ученика (Miro: Серия выполненных ДЗ).
    """
    user_id = int(current_user["sub"])
    streaks_data = await UserRepository.get_student_streaks(db=db, student_id=user_id)
    return streaks_data

@student_router.get(
    "/debts", response_model=list[StudentDebtResponse], status_code=status.HTTP_200_OK
)
async def get_debts(
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получение списка открытых задолженностей ученика (Miro: Мои задолженности).
    """
    user_id = int(current_user["sub"])
    debts_data = await UserRepository.get_student_debts(db=db, student_id=user_id)
    return debts_data

@student_router.get(
    "/mascot",
    response_model=MascotResponse,
    status_code=status.HTTP_200_OK,
)
async def get_mascot(
    subject_id: int | None = Query(
        None, description="ID предмета. Без параметра берётся первый предмет класса."
    ),
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Маскот предмета и текущий стрик по ДЗ (Miro: «Огонёк»).
    Картинки живут на фронтенде, бэк отдаёт только тип и текст.
    """
    student_id = int(current_user["sub"])

    # 1. Получаем список предметов класса
    dashboard = await UserRepository.get_student_dashboard_data(
        db=db, student_id=student_id
    )
    subjects = dashboard.get("subjects", [])
    if not subjects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У класса ученика нет предметов.",
        )

    # 2. Определяем нужный предмет
    if subject_id is None:
        subject = subjects[0]
    else:
        subject = next(
            (s for s in subjects if s["subject_id"] == subject_id), None
        )
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Предмет не найден в вашем классе.",
            )

    # 3. Получаем стрик по предмету (0, если ещё нет)
    streaks = await UserRepository.get_student_streaks(
        db=db, student_id=student_id
    )
    current_streak = next(
        (
            s["current_streak"]
            for s in streaks
            if s["subject_id"] == subject["subject_id"]
        ),
        0,
    )

        # Определяем mascot_type по названию предмета
    name = subject["name"].lower()
    
    # ВАЖНО: Физкультуру проверяем ДО физики, иначе сработает "физ"
    if "физкульт" in name or "физ. культ" in name:
        m_type = "pe"
    elif "труд" in name or "технолог" in name:
        m_type = "trud"
    elif "матем" in name:
        m_type = "math"
    elif "русск" in name:
        m_type = "russian"
    elif "литерат" in name:
        m_type = "literature"
    elif "истори" in name:
        m_type = "history"
    elif "географ" in name:
        m_type = "geography"
    elif "хими" in name:
        m_type = "chemistry"
    elif "информ" in name:
        m_type = "informatics"
    elif "биолог" in name:
        m_type = "biology"
    elif "английск" in name or "иностран" in name:
        m_type = "english"
    elif "физ" in name:
        m_type = "physics"
    else:
        m_type = "default"

    # 5. Формируем текст (без ИИ)
    if current_streak <= 0:
        message = (
            f"Серия ДЗ по предмету «{subject['name']}» пока не началась. "
            f"Сдай следующее ДЗ на 3 и выше — огонёк загорится."
        )
    else:
        message = (
            f"Огонёк горит: {current_streak} ДЗ подряд по предмету "
            f"«{subject['name']}». Так держать!"
        )

    return {
        "subject_id": subject["subject_id"],
        "mascot_type": m_type,
        "current_streak": current_streak,
        "message": message,
    }

@student_router.post(
    "/debts/{debt_id}/prep-test",
    response_model=PrepTestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prep_test(
    debt_id: int,
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    C2: тренировочный тест по долгу.
    """
    student_id = int(current_user["sub"])

    # 1. Долг: существует, принадлежит ученику, не закрыт
    debt = await db.get(DebtModel, debt_id)
    if not debt or debt.student_id != student_id or debt.resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задолженность не найдена.",
        )

    # 2. Урок
    lesson = await db.get(LessonModel, debt.lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="По этому долгу нет урока.",
        )

    # 3. Ищем тему
    topic_id = lesson.topic_id
    topic_title = None

    if topic_id is not None:
        topic = await db.get(PlanTopicModel, topic_id)
        if topic:
            topic_title = topic.title

    # Если в уроке нет темы, пробуем взять из ДЗ, иначе ищем первую тему в плане
    if not topic_title:
        topic_title = lesson.homework

    if topic_id is None:
        # Чтобы создать тест, нужен валидный topic_id. Ищем любую тему из плана класса.
        topic_q = (
            select(PlanTopicModel)
            .join(StudyPlanModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
            .where(
                StudyPlanModel.class_id == lesson.class_id,
                StudyPlanModel.subject_id == lesson.subject_id,
            )
            .limit(1)
        )
        fallback_topic = (await db.execute(topic_q)).scalar_one_or_none()
        
        if fallback_topic:
            topic_id = fallback_topic.topic_id
            if not topic_title:
                topic_title = fallback_topic.title
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="По этому долгу нет темы (в плане класса нет тем).",
            )

    # 4. Ищем существующий prep-тест
    existing_q = (
        select(TestModel)
        .where(
            TestModel.topic_id == topic_id,
            TestModel.status == "prep",
        )
        .options(selectinload(TestModel.questions))
        .limit(1)
    )
    prep_test = (await db.execute(existing_q)).scalar_one_or_none()

    # 5. Генерируем новый, если нет
    if prep_test is None:
        prep_test = await UserRepository.generate_ai_test(
            db=db, topic=topic_title or "Без темы", topic_id=topic_id
        )
        prep_test.status = "prep"
        await db.flush()

    return prep_test