from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from scr.model.model import UserModel, StudyPlanModel, PlanTopicModel, TestModel
from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.api.auth_deps import require_role
from scr.schemas.test_schemas import (
    TestResponse,
    SubmitTestRequest,
    SubmitTestResponse,
    AIFeedbackResponse,
    AIFeedbackItem,
)
from scr.config import settings
tests_router = APIRouter(prefix="/tests", tags=["Тестирование"])

MAX_ATTEMPTS = 3  # C4: лимит попыток на published-тест


async def _is_student(db: AsyncSession, user_id: int) -> bool:
    """Проверяем роль через БД — надёжнее, чем парсить JWT."""
    user = await UserRepository.get_user_by_id(db, user_id)
    if not user:
        return False
    role = getattr(user.role, "value", user.role)
    return str(role) == "student"

async def _check_student_test_access(db: AsyncSession, student_id: int, test_id: int):
    """D2: Проверяет, что тест относится к классу ученика."""
    student = await db.get(UserModel, student_id)
    if not student or not student.class_id:
        raise HTTPException(status_code=403, detail="Ученик не привязан к классу.")

    stmt = (
        select(StudyPlanModel.class_id)
        .join(PlanTopicModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
        .join(TestModel, TestModel.topic_id == PlanTopicModel.topic_id)
        .where(TestModel.test_id == test_id)
    )
    test_class_id = (await db.execute(stmt)).scalar_one_or_none()

    if test_class_id is not None and test_class_id != student.class_id:
        raise HTTPException(status_code=403, detail="Этот тест предназначен для другого класса.")

@tests_router.get(
    "/{test_id}",
    response_model=TestResponse,
    status_code=status.HTTP_200_OK,
)
async def get_test(
    test_id: int,
    current_user: dict = Depends(require_role(["student", "teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Возвращает структуру теста и вопросы (§9.7).
    C4: черновики (draft) ученику не видны — 404.
    """
    test = await UserRepository.get_test_with_questions(db=db, test_id=test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запрашиваемый ИИ-тест не найден в системе.",
        )

    # C4: черновик доступен только учителю
    if test.status not in ("published", "prep") and await _is_student(
        db, int(current_user["sub"])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запрашиваемый ИИ-тест не найден в системе.",
        )
    if await _is_student(db, int(current_user["sub"])):
        await _check_student_test_access(db, int(current_user["sub"]), test_id)
    return test


@tests_router.post(
    "/{test_id}/submit",
    response_model=SubmitTestResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_test(
    test_id: int,
    payload: SubmitTestRequest,
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Принимает ответы ученика (§9.7).
    C4: 
    - черновик → 404
    - лимит 3 попытки для published → 409
    - prep-тесты без лимита (для C2)
    - тест без вопросов → 422
    """
    test = await UserRepository.get_test_with_questions(db=db, test_id=test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест не найден. Невозможно зафиксировать ответы.",
        )

    if test.status not in ("published", "prep"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест не найден. Невозможно зафиксировать ответы.",
        )

    student_id = int(current_user["sub"])
    await _check_student_test_access(db, student_id, test_id)

    # C4: лимит 3 попытки для published (prep — без лимита)
    if test.status == "published":
        used = await UserRepository.count_completed_attempts(
            db=db, student_id=student_id, test_id=test_id
        )
        if used >= MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Все попытки по этому тесту использованы.",
            )

    result = await UserRepository.submit_test_answers(
        db=db, student_id=student_id, test_id=test_id, user_answers=payload.answers
    )

    # C4: если в результате нет attempt_id (например, у теста нет вопросов) → 422
    if "attempt_id" not in result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.get("message", "Не удалось обработать ответы."),
        )

    return result

@tests_router.get(
    "/{test_id}/ai-feedback",
    response_model=AIFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def get_ai_feedback(
    test_id: int,
    attempt_id: int,
    current_user: dict = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db_session),
):
    """
    C3: Разбор ошибок после сдачи теста.
    """
    student_id = int(current_user["sub"])

    data = await UserRepository.get_ai_feedback_data(
        db=db, test_id=test_id, attempt_id=attempt_id, student_id=student_id
    )

    if data["error"] == "not_found":
        raise HTTPException(status_code=404, detail="Попытка или тест не найдены.")
    if data["error"] == "forbidden_owner":
        raise HTTPException(status_code=403, detail="Это не ваша попытка.")

    items = []
    for db_answer, db_question in data["incorrect_answers"]:
        user_ans_str = db_answer.answer
        correct_ans_str = ""
        
        # Безопасно приводим Enum к строке
        q_type = str(db_question.type.value if hasattr(db_question.type, 'value') else db_question.type).lower()

        if "choice" in q_type and db_question.options:
            options_list = db_question.options.get("options", [])
            try:
                idx = int(db_answer.answer)
                if 0 <= idx < len(options_list):
                    user_ans_str = options_list[idx]
            except (ValueError, TypeError):
                pass
            
            if db_question.correct_option_index is not None and 0 <= db_question.correct_option_index < len(options_list):
                correct_ans_str = options_list[db_question.correct_option_index]
                
        elif "numeric" in q_type:
            if db_question.numeric_answer is not None:
                correct_ans_str = f"{float(db_question.numeric_answer):g}"

        # Генерируем пояснение
        explanation = f"Правильный ответ: {correct_ans_str}."
        if settings.USE_MOCK_LLM:
            explanation = f"Мок-объяснение: правильный ответ — {correct_ans_str}. Повторите тему."
        else:
            try:
                from scr.services.llm_service import YandexGPTService
                prompt = (
                    f"Кратко объясни школьнику, почему на вопрос '{db_question.question}' "
                    f"правильный ответ — '{correct_ans_str}', а его ответ '{user_ans_str}' неверен. "
                    f"Ответь одним коротким предложением."
                )
                ai_exp = await YandexGPTService.generate_text(prompt)
                if ai_exp:
                    explanation = ai_exp
            except Exception as e:
                print(f"⚠️ Ошибка генерации объяснения: {e}")

        items.append(AIFeedbackItem(
            question_id=db_question.question_id,
            question=db_question.question,
            your_answer=str(user_ans_str),
            correct_answer=str(correct_ans_str),
            explanation=explanation
        ))

    return AIFeedbackResponse(attempt_id=attempt_id, items=items)