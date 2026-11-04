from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import os
from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.api.auth_deps import require_role, get_current_token_data
from scr.schemas.teacher_schemas import TeacherClassResponse
from scr.schemas.generation_schemas import GenerateTestRequest, GenerateTestResponse
from scr.schemas.publish_schemas import PublishTestResponse, PublishTestRequest
from scr.schemas.test_schemas import TestSaveRequest, TestResponse
from scr.services.logger_service import StructuredLogger
from fastapi import UploadFile, File
from scr.services.journal_excel_service import parse_journal_excel
from scr.services.journal_import_service import JournalImportService
from scr.schemas.teacher_dashboard_schemas import TeacherDashboardResponse
from scr.schemas.topic_schemas import TopicLookupSchema
from scr.model.model import LessonModel, TestModel, StudyPlanModel, PlanTopicModel
from sqlalchemy import select
from scr.schemas.test_schemas import TestEditResponse, QuestionEditResponse

teacher_router = APIRouter(prefix="/teacher", tags=["Панель Учителя"])


@teacher_router.get(
    "/topics",
    response_model=list[TopicLookupSchema],
    status_code=status.HTTP_200_OK,
)
async def get_topics(
    current_user: dict = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получение списка тем учебного плана.
    ПРАВКА: Идентификатор учителя берется из JWT-токена, предмет определяется автоматически.
    """
    # Теперь current_user используется на 100% для бизнес-логики и безопасности!
    teacher_id = int(current_user["sub"])

    topics = await UserRepository.get_topics_by_teacher_subject(
        db=db, teacher_id=teacher_id
    )
    return topics


@teacher_router.get(
    "/dashboard",
    response_model=TeacherDashboardResponse,
    status_code=status.HTTP_200_OK,
)
async def get_teacher_dashboard(
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Эндпоинт для главного экрана учителя (§9.5 ТЗ, страница 5 Контракта).
    Возвращает полную сводку по классам, метрики задолженностей, темы на завтра и сетку ИИ-тестов.
    """
    teacher_id = int(current_user["sub"])

    # Запрашиваем собранные и отфильтрованные данные напрямую у репозитория
    dashboard_data = await UserRepository.get_teacher_dashboard_counters(
        db=db, teacher_id=teacher_id
    )
    return dashboard_data


@teacher_router.get(
    "/classes",
    response_model=list[TeacherClassResponse],
    status_code=status.HTTP_200_OK,
)
async def get_teacher_classes(
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Получение списка всех классов, закрепленных за текущим учителем (§9.1, §9.4).
    Извлекает user_id напрямую из проверенного payload JWT-токена.
    """
    teacher_id = int(current_user["sub"])
    school_classes = await UserRepository.get_teacher_classes(
        db=db, teacher_id=teacher_id
    )

    if not school_classes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="За данным учителем не закреплено ни одного класса в текущем учебном году.",
        )
    return school_classes


@teacher_router.post("/tests/generate", response_model=GenerateTestResponse, status_code=status.HTTP_201_CREATED)
async def generate_test(
    payload: GenerateTestRequest,
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    teacher_id = int(current_user["sub"])
    topic_name = await UserRepository.get_topic_title_for_teacher(db, payload.topic_id, teacher_id)
    if not topic_name:
        raise HTTPException(status_code=404, detail=f"Тема с id={payload.topic_id} не найдена")

    test_data = await UserRepository.generate_ai_test(
        db=db, 
        topic=topic_name, 
        topic_id=payload.topic_id,
        class_id=payload.class_id,
        title=payload.title,
        question_count=payload.question_count,
        question_type=payload.question_type
    )
    return test_data

@teacher_router.post(
    "/tests/publish", response_model=PublishTestResponse, status_code=status.HTTP_200_OK
)
async def publish_test(
    payload: PublishTestRequest,
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Публикация теста и привязка к уроку.
    D3: Проверяет, что и тест, и урок принадлежат этому учителю.
    """
    teacher_id = int(current_user["sub"])

    # D3: Проверяем, что тест принадлежит этому учителю (через тему -> учебный план)
    test_owner_q = (
        select(StudyPlanModel.teacher_id)
        .join(PlanTopicModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
        .join(TestModel, TestModel.topic_id == PlanTopicModel.topic_id)
        .where(TestModel.test_id == payload.test_id)
    )
    test_teacher_id = (await db.execute(test_owner_q)).scalar_one_or_none()
    
    if test_teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Вы не можете публиковать чужие тесты.")

    # D3: Проверяем, что урок принадлежит этому учителю
    lesson = await db.get(LessonModel, payload.lesson_id)
    if not lesson or lesson.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Урок не найден или принадлежит другому учителю.")

    # Публикуем
    updated_lesson = await UserRepository.publish_test_to_lesson(
        db=db, test_id=payload.test_id, lesson_id=payload.lesson_id
    )

    if not updated_lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не удалось опубликовать тест. Проверьте валидность test_id и UUID lesson_id",
        )

    # Исправляем баг с именем поля (homework вместо homework_text)
    homework_updated_text = getattr(updated_lesson, "homework", "") or ""

    return {
        "message": "Тест успешно опубликован и привязан к уроку",
        "test_id": payload.test_id,
        "lesson_id": payload.lesson_id,
        "homework_updated_text": homework_updated_text,
    }
@teacher_router.patch("/debts/{debt_id}", status_code=status.HTTP_200_OK)
async def patch_debt(
    debt_id: int,
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Ручное закрытие задолженности ученика учителем (§9.5, §10.2).
    С автоматической фиксацией в транзакционном журнале аудит-логов (§13.4).
    """
    teacher_id = int(current_user["sub"])

    result = await UserRepository.resolve_debt_manual(
        db=db, debt_id=debt_id, teacher_id=teacher_id
    )

    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=result["message"]
        )

    if result["status"] == "skipped":
        return {
            "message": "Задолженность уже была закрыта ранее",
            "skipped": "already_resolved",
        }

    # Пишем аудит лог в той же транзакции бд (§13.4)
    await UserRepository.write_audit_log(
        db=db,
        action="debt.resolve",
        target_type="debt",
        target_id=str(debt_id),
        actor_id=teacher_id,
        payload={"method": "manual"},
    )

    # Выводим структурированный лог в консоль в формате JSON Lines (§13.5)
    StructuredLogger.log(
        level="INFO",
        event="debt_resolved_by_teacher",
        context={"debt_id": debt_id},
        user_id=teacher_id,
    )

    return {"message": "Задолженность успешно закрыта учителем", "debt_id": debt_id}

@teacher_router.post("/journal/import", status_code=status.HTTP_200_OK)
async def import_eriso_journal(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Импорт выгрузки ЕРИСО КО (.xlsx) (A4).
    Использует journal_excel_service (без хардкода student_id/class_id) и
    journal_import_service (создаёт/обновляет темы, уроки, оценки; дедуп).
    """
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Разрешены только файлы .xlsx",
        )

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # D5: защита от больших файлов
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Файл больше 5 МБ",
        )

    temp_path = f"/tmp/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка сохранения файла: {e}",
        )

    try:
        rows, parse_errors = parse_journal_excel(temp_path)
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="В файле нет корректных строк для импорта",
            )

        result = await JournalImportService.import_rows(
            db=db,
            teacher_id=int(current_user["sub"]),
            school_id=1,  # пилотная школа №1
            rows=rows,
        )

        await UserRepository.write_sync_log(
            db=db,
            entity="excel_import",
            entity_id=file.filename,
            status="ok",
            payload={
                "lessons_processed": result["lessons_processed"],
                "grades_processed": result["grades_processed"],
            },
        )

        # ошибки по строкам + предупреждения парсера, не больше 20
        all_errors = (result["errors"] + parse_errors)[:20]

        return {
            "message": "Синхронизация данных ЕРИСО КО успешно завершена.",
            "lessons_processed": result["lessons_processed"],
            "grades_processed": result["grades_processed"],
            "skipped_rows": result["skipped_rows"],
            "errors": all_errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка разбора ведомости ЕРИСО КО: {e}",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
@teacher_router.put("/tests/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: int,
    payload: TestSaveRequest,
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """Сохранение отредактированного черновика теста (Конструктор)."""
    teacher_id = int(current_user["sub"])
    updated_test = await UserRepository.update_test_questions(
        db=db, test_id=test_id, teacher_id=teacher_id, payload=payload
    )
    if not updated_test:
        raise HTTPException(status_code=400, detail="Тест не найден или уже опубликован (редактировать можно только черновики).")
    return updated_test

@teacher_router.get("/tests/{test_id}", response_model=TestEditResponse, status_code=status.HTTP_200_OK)
async def get_test_for_edit(
    test_id: int,
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """Получение теста для редактирования (с правильными ответами)."""
    test = await UserRepository.get_test_with_questions(db=db, test_id=test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден.")

    questions = []
    for q in test.questions:
        opts = q.options or {}
        correct_indices = None
        numeric_answer = None
        q_type_str = q.type.value if hasattr(q.type, "value") else str(q.type)

        if q_type_str == "numeric" or q_type_str == "math":
            numeric_answer = float(q.numeric_answer) if q.numeric_answer is not None else None
            opts = None
        else:
            if opts.get("is_multiple"):
                correct_indices = opts.get("correct_indices", [])
            elif opts.get("is_text"):
                correct_indices = [0] # Схема для текста
            elif q.correct_option_index is not None:
                correct_indices = [q.correct_option_index]

        questions.append(QuestionEditResponse(
            question_id=q.question_id,
            type=q_type_str,
            question=q.question,
            options=opts,
            correct_indices=correct_indices,
            numeric_answer=numeric_answer
        ))

    return TestEditResponse(
        test_id=test.test_id,
        topic_id=test.topic_id,
        created_by=test.created_by.value if hasattr(test.created_by, "value") else str(test.created_by),
        status=test.status,
        title=test.title,
        questions=questions
    )
@teacher_router.delete("/tests/{test_id}", status_code=status.HTTP_200_OK)
async def delete_test(
    test_id: int,
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Удаление теста (например, неудачного черновика из конструктора).
    """
    teacher_id = int(current_user["sub"])
    
    success = await UserRepository.delete_test(
        db=db, test_id=test_id, teacher_id=teacher_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тест не найден или принадлежит другому учителю."
        )
        
    return {"message": "Тест успешно удален", "test_id": test_id}