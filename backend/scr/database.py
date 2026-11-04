import asyncio
import datetime
import uuid
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, InterfaceError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from scr.config import settings
from scr.model.model import (
    Base,
    SchoolClassesModel,
    UserModel,
    UserRole,
    SubjectModel,
    ClassSubjectModel,
    StreakModel,
    DebtModel,
    DebtType,
    LessonModel,
    GradeModel,
    TestModel,
    PlanTopicModel,
    TestQuestionModel,
    StudyPlanModel,
    QuestionType,
    TestCreatedBy,
)

DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=True)
create_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_db():
    async with create_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e


async def get_db_session():
    """Обычный асинхронный генератор сессии для FastAPI Depends"""
    async with create_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e


async def init_db():
    max_retries = 5
    retry_delay = 2

    print("⏳ Ожидание полной готовности базы данных...")
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("🚀 База данных «Умного дневника» успешно инициализирована и готова!")
            return
        except (OperationalError, InterfaceError, Exception) as e:
            print(
                f"⚠️ База данных еще не готова (Попытка {attempt}/{max_retries}). Ошибка: {type(e).__name__}"
            )
            if attempt == max_retries:
                raise e
            await asyncio.sleep(retry_delay)


async def seed_demo_data():
    """
    Полностью идемпотентная функция заполнения демо-данных.
    Очищена от дублирования кода, повторных вставок и конфликтов vk_id.
    """
    async with create_session() as session:
        async with session.begin():
            # 1. Защита от дублирования: проверяем наличие демо-учителя по его ID
            check_teacher = await session.execute(
                select(UserModel).where(UserModel.user_id == 12)
            )
            if check_teacher.scalar_one_or_none() is not None:
                print(
                    "✅ [SEED] Демо-данные уже зафиксированы в СУБД. Наполнение пропущено."
                )
                return

            print("🌱 [SEED] Инициализация демо-сценария для хакатона...")

            # 2. Создаем демонстрационный класс (7А) по ТЗ v6.0 (§15.4)
            demo_class = SchoolClassesModel(
                class_id=7,
                class_name="7А",
                parallel=7,
                academic_year=2026,
            )
            session.add(demo_class)

            # 3. Создаем справочник предметов
            math_subject = SubjectModel(subject_id=3, name="Математика")
            russian_subject = SubjectModel(subject_id=4, name="Русский язык")
            physics_subject = SubjectModel(subject_id=5, name="Физика")
            session.add_all([math_subject, russian_subject, physics_subject])

            # 4. Создаем Учителя (vk_id совпадает с моком "teacher" для входа)
            demo_teacher = UserModel(
                user_id=12,
                vk_id=12345,
                full_name="Соколова Марина Петровна",
                role=UserRole.TEACHER,
                class_id=None,
                avatar_url="https://dicebear.com",
            )

            # 5. Создаем Ученика (Иванов Иван из 7А, vk_id совпадает с моком "student")
            demo_student = UserModel(
                user_id=21,
                vk_id=23456,
                full_name="Иванов Иван Сергеевич",
                role=UserRole.STUDENT,
                class_id=7,
                avatar_url="https://dicebear.com",
            )
            session.add_all([demo_teacher, demo_student])

            # Фиксируем сущности в памяти транзакции, чтобы связать их внешними ключами
            await session.flush()

            # 6. Закрепляем Математику в классе 7А за Учителем
            teacher_load = ClassSubjectModel(
                class_id=7,
                subject_id=3,
                teacher_id=12,
                schedule={"days": ["Monday", "Wednesday", "Friday"]},
            )
            session.add(teacher_load)

            # 7. Генерируем детерминированный UUIDv5 для урока согласно §11.1.2 ТЗ
            demo_lesson_id = uuid.uuid5(uuid.NAMESPACE_DNS, "7|3|2026-10-15|0")

            demo_lesson = LessonModel(
                lesson_id=demo_lesson_id,
                class_id=7,
                subject_id=3,
                teacher_id=12,
                lesson_date=datetime.date(2026, 10, 15),
                homework="Повторить теорию дискриминанта",
                academic_year=2026,
            )
            session.add(demo_lesson)
            await session.flush()

            # 8. Зажигаем ученику стрик по Математике
            math_streak = StreakModel(
                student_id=21,
                subject_id=3,
                current_streak=5,
                last_homework_done=datetime.date(2026, 10, 16),
                academic_year=2026,
            )
            session.add(math_streak)

            # 9. Вешаем на ученика ДОЛГ, привязанный к UUID урока
            demo_debt = DebtModel(
                student_id=21,
                lesson_id=demo_lesson_id,
                type=DebtType.HOMEWORK,
                resolved=False,
                academic_year=2026,
            )
            session.add(demo_debt)

            # 10. Создаем оценку
            demo_grade = GradeModel(
                grade_id=1,
                lesson_id=demo_lesson_id,
                student_id=21,
                value=4,
                academic_year=2026,
            )
            session.add(demo_grade)

            # 11. Создаем учебный план и тему урока (Внешние ключи FK)
            demo_plan = StudyPlanModel(
                plan_id=1, class_id=7, subject_id=3, teacher_id=12
            )
            session.add(demo_plan)

            demo_topic = PlanTopicModel(
                topic_id=1,
                plan_id=1,
                order_num=1,
                title="Квадратные уравнения",
                hours=4,
                quarter=1,
                is_current=True,
            )
            session.add(demo_topic)
            await session.flush()

            # 12. Создаем тест (ID 55) со статусом published
            demo_test = TestModel(
                test_id=55,
                topic_id=1,
                created_by=TestCreatedBy.MANUAL,
                status="published",
            )
            session.add(demo_test)
            await session.flush()

            # 13. Добавляем вопросы в тест, используя исходные поля и типы вашей модели
            q1 = TestQuestionModel(
                question_id=1,
                test_id=55,
                type=QuestionType.CHOICE,
                question="Чему равен дискриминант, если уравнение имеет ровно 1 корень?",
                options={"options": ["D > 0", "D = 0", "D < 0"]},
                correct_option_index=1,
                numeric_answer=None,
            )

            q2 = TestQuestionModel(
                question_id=2,
                test_id=55,
                type=QuestionType.NUMERIC,
                question="Сколько корней имеет уравнение, если дискриминант меньше нуля?",
                options=None,
                correct_option_index=None,
                numeric_answer=0.0,
            )
            session.add_all([q1, q2])

            print(
                "🌱 [SEED] Демо-сценарий успешно развернут! База данных готова к показу."
            )
