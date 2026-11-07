from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import random
from scr.model.model import (
    UserModel,
    SchoolClassesModel,
    ClassSubjectModel,
    LessonModel,
    GradeModel,
    PlanTopicModel,
    StreakModel,
    SubjectModel,
    TestModel,
    TestQuestionModel,
    TestAttemptModel,
    TestAnswerModel,
    TestAttemptStatus,
    SeatingModel,
    DebtModel,
    QuestionType,
    TestCreatedBy,
    GradeSource,
    UserRole,
)
import datetime
import uuid
import os
from scr.config import settings
from scr.services.text_service import TextNormalizationService


class UserRepository:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
        """
        Ищет пользователя в базе данных по email.
        (Поскольку в демо-сиде email записан в поле full_name, ищем по нему)
        """
        query = select(UserModel).where(UserModel.full_name == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> UserModel | None:
        """
        Ищет пользователя в базе данных по его уникальному user_id.
        """
        query = select(UserModel).where(UserModel.user_id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_teacher_classes(
        db: AsyncSession, teacher_id: int
    ) -> list[SchoolClassesModel]:
        """
        ИСПРАВЛЕНО ИМЯ МЕТОДА: get_teacher_classes вместо get_teacher_class
        Вытаскивает из базы данных список ВСЕХ классов, в которых ведет уроки учитель (§9.1, §9.4).
        """
        query = (
            select(SchoolClassesModel)
            .join(
                ClassSubjectModel,
                SchoolClassesModel.class_id == ClassSubjectModel.class_id,
            )
            .where(ClassSubjectModel.teacher_id == teacher_id)
            .distinct()
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_class_journal(
        db: AsyncSession,
        class_id: int,
        subject_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[LessonModel]:
        """
        ИСПРАВЛЕНО: Добавлены аргументы limit и offset для постраничной пагинации уроков (§9.1).
        Вытаскивает пагинированный список уроков класса по предмету за текущий учебный год.
        """
        current_year = UserRepository._get_current_academic_year()

        query = (
            select(LessonModel)
            .where(
                LessonModel.class_id == class_id,
                LessonModel.subject_id == subject_id,
                LessonModel.academic_year == current_year,
            )
            .options(selectinload(LessonModel.grades))
            # Принудительно сортируем по дате и номеру урока для корректного среза страниц
            .order_by(LessonModel.lesson_date.desc(), LessonModel.lesson_number.asc())
            # Накладываем ограничения среза страниц строго по ТЗ
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_student_streaks(db: AsyncSession, student_id: int) -> list[dict]:
        """
        Вытаскивает из базы данных все активные серии (стрики) выполненных ДЗ
        для конкретного ученика с названиями предметов.
        """
        # Делаем SELECT из таблицы стриков, джойним предметы для получения названия
        query = (
            select(StreakModel)
            .where(StreakModel.student_id == student_id)
            .options(
                selectinload(StreakModel.subject)
            )  # Жадно подгружаем связь с предметом
        )
        result = await db.execute(query)
        streaks = result.scalars().all()

        # Превращаем в плоскую структуру для удобства маппинга в Pydantic-схему
        formatted_streaks = []
        for streak in streaks:
            formatted_streaks.append(
                {
                    "subject_id": streak.subject_id,
                    "subject_name": streak.subject.name,
                    "current_streak": streak.current_streak,
                    "last_homework_done": streak.last_homework_done,
                }
            )

        return formatted_streaks

    @staticmethod
    async def get_student_grades(db: AsyncSession, student_id: int) -> list[dict]:
        """
        Вытаскивает из базы данных все оценки ученика с датами уроков и названиями предметов.
        """
        # Делаем SELECT из таблицы оценок, фильтруем по student_id
        query = (
            select(GradeModel)
            .where(GradeModel.student_id == student_id)
            .options(
                selectinload(GradeModel.lesson).selectinload(
                    LessonModel.subject
                )  # Цепочкой подгружаем урок и предмет
            )
        )
        result = await db.execute(query)
        grades = result.scalars().all()

        # Форматируем в плоский вид для схемы
        formatted_grades = []
        for grade in grades:
            formatted_grades.append(
                {
                    "grade_id": grade.grade_id,
                    "value": grade.value,
                    "subject_name": (
                        grade.lesson.subject.name
                        if grade.lesson and grade.lesson.subject
                        else "Неизвестно"
                    ),
                    "lesson_date": (
                        grade.lesson.lesson_date
                        if grade.lesson
                        else datetime.date.today()
                    ),
                }
            )

        return formatted_grades

    @staticmethod
    async def get_test_with_questions(
        db: AsyncSession, test_id: int
    ) -> TestModel | None:
        """Вытягивает тест вместе с вопросами из базы данных"""
        query = (
            select(TestModel)
            .where(TestModel.test_id == test_id)
            .options(selectinload(TestModel.questions))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def submit_test_answers(
        db: AsyncSession, student_id: int, test_id: int, user_answers: list
    ) -> dict:
        """
        Принимает ответы ученика, рассчитывает балл.
        Поддерживает: single_choice, multiple_choice, text_input, numeric.
        """
        from decimal import Decimal
        from scr.model.model import (
            TestQuestionModel,
            TestAttemptModel,
            TestAnswerModel,
            TestAttemptStatus,
            QuestionType,
        )

        query = select(TestQuestionModel).where(TestQuestionModel.test_id == test_id)
        result = await db.execute(query)
        questions = result.scalars().all()

        if not questions:
            return {"status": "error", "message": "Вопросы теста не найдены"}

        answers_dict = {a.question_id: a.answer for a in user_answers}

        attempt = TestAttemptModel(
            test_id=test_id,
            student_id=student_id,
            score=0,
            status=TestAttemptStatus.IN_PROGRESS,
        )
        db.add(attempt)
        await db.flush()

        total_earned_points = Decimal("0.0")
        total_questions_count = len(questions)

        for q in questions:
            user_ans = answers_dict.get(q.question_id, "")
            is_question_correct = False
            question_points = Decimal("0.0")

            # --- 1. Числовые ответы (math / numeric) ---
            if q.type == QuestionType.NUMERIC and q.numeric_answer is not None:
                try:
                    # Используем допуск (tolerance) для сравнения чисел
                    user_val = float(str(user_ans).replace(",", "."))
                    correct_val = float(q.numeric_answer)
                    if abs(user_val - correct_val) < 1e-6:  # Допуск
                        is_question_correct = True
                        question_points = Decimal("1.0")
                except (ValueError, TypeError):
                    pass

            # --- 2. Одиночный выбор (single_choice) ---
            elif q.type == QuestionType.CHOICE and not q.options.get("is_multiple") and not q.options.get("is_text"):
                if q.correct_option_index is not None:
                    options_list = q.options.get("options", [])
                    correct_text = options_list[q.correct_option_index] if q.correct_option_index < len(options_list) else ""
                    # Сравниваем и индекс, и текст
                    if (str(q.correct_option_index) == str(user_ans).strip() or
                        str(user_ans).strip().lower() == str(correct_text).lower()):
                        is_question_correct = True
                        question_points = Decimal("1.0")

            # --- 3. Множественный выбор (multiple_choice) ---
            elif q.type == QuestionType.CHOICE and q.options.get("is_multiple"):
                correct_indices = set(q.options.get("correct_indices", []))
                try:
                    # Ожидаем от фронтенда строку с индексами через запятую (например, "0,2")
                    user_indices = set(int(i) for i in str(user_ans).split(',') if i.strip().isdigit())
                    if user_indices == correct_indices:
                        is_question_correct = True
                        question_points = Decimal("1.0")
                except Exception:
                    pass

            # --- 4. Текстовый ответ (text_input) ---
            elif q.type == QuestionType.CHOICE and q.options.get("is_text"):
                correct_text = q.options.get("correct_text", "").strip().lower()
                user_text = str(user_ans).strip().lower()
                # Простая нормализация: убираем лишние пробелы и сравниваем
                if " ".join(user_text.split()) == " ".join(correct_text.split()):
                    is_question_correct = True
                    question_points = Decimal("1.0")
            # --- 5. Сопоставление (matching) ---
            elif q.type == QuestionType.MATCHING:
                correct_matches = q.options.get("correct_matches", {}) if q.options else {}
                try:
                    user_pairs = {}
                    if user_ans:
                        ans_str = str(user_ans).strip()
                        # 1. Пробуем распарсить как JSON (современный формат)
                        if ans_str.startswith('{') and ans_str.endswith('}'):
                            import json
                            user_pairs = json.loads(ans_str)
                        # 2. Фолбэк на старый формат "Лево1-Право1,Лево2-Право2"
                        else:
                            for pair in ans_str.split(','):
                                if '-' in pair:
                                    left, right = pair.split('-', 1)
                                    user_pairs[left.strip()] = right.strip()

                    if user_pairs and user_pairs == correct_matches:
                        is_question_correct = True
                        question_points = Decimal("1.0")
                except Exception as e:
                    print(f"⚠️ Ошибка проверки matching: {e}")
                    pass
            total_earned_points += question_points

            db_answer = TestAnswerModel(
                attempt_id=attempt.attempt_id,
                question_id=q.question_id,
                answer=str(user_ans),
                is_correct=is_question_correct,
            )
            db.add(db_answer)

        final_percent = 0
        if total_questions_count > 0:
            raw_percent = (total_earned_points / Decimal(str(total_questions_count))) * Decimal("100.0")
            final_percent = int(raw_percent.quantize(Decimal("1"), rounding="ROUND_HALF_UP"))

        is_passed = final_percent >= 70

        attempt.score = final_percent
        attempt.status = TestAttemptStatus.COMPLETED
        attempt.passed_at = datetime.datetime.now(datetime.timezone.utc) if is_passed else None

        await db.flush()

        return {
            "attempt_id": attempt.attempt_id,
            "score": final_percent,
            "passed": is_passed,
        }

    @staticmethod
    async def get_ai_feedback_data(
        db: AsyncSession, test_id: int, attempt_id: int, student_id: int
    ) -> dict:
        """Собирает данные для разбора ошибок."""
        from scr.model.model import (
            TestAttemptModel, TestAnswerModel, TestQuestionModel, TestModel
        )

        # 1. Ищем попытку
        attempt = await db.get(TestAttemptModel, attempt_id)
        if not attempt or attempt.test_id != test_id:
            return {"error": "not_found"}
        
        if attempt.student_id != student_id:
            return {"error": "forbidden_owner"}

        # 2. Достаем неверные ответы (без блокировок для демо)
        answers_q = (
            select(TestAnswerModel, TestQuestionModel)
            .join(TestQuestionModel, TestAnswerModel.question_id == TestQuestionModel.question_id)
            .where(
                TestAnswerModel.attempt_id == attempt_id,
                TestAnswerModel.is_correct == False
            )
        )
        rows = (await db.execute(answers_q)).all()

        return {
            "error": None,
            "test_status": attempt.test_id, 
            "incorrect_answers": rows
        }

    @staticmethod
    async def count_completed_attempts(
        db: AsyncSession, student_id: int, test_id: int
    ) -> int:
        """
        C4: количество завершённых попыток по тесту.
        Для лимита в 3 попытки на published-тест.
        """
        stmt = select(func.count(TestAttemptModel.attempt_id)).where(
            TestAttemptModel.student_id == student_id,
            TestAttemptModel.test_id == test_id,
            TestAttemptModel.status == TestAttemptStatus.COMPLETED,
        )
        return int((await db.execute(stmt)).scalar_one())

    @staticmethod
    async def get_class_seating(db: AsyncSession, class_id: int) -> SeatingModel | None:
        """Получает текущую рассадку для конкретного класса"""
        query = select(SeatingModel).where(SeatingModel.class_id == class_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def save_class_seating(
        db: AsyncSession, class_id: int, layout: dict, teacher_pos: str
    ) -> SeatingModel:
        """
        Сохраняет или обновляет рассадку класса.
        Автоматически пишет вычисленную позицию учителя.
        """
        # Ищем, была ли рассадка до этого
        query = select(SeatingModel).where(SeatingModel.class_id == class_id)
        result = await db.execute(query)
        seating = result.scalar_one_or_none()

        if seating:
            # Обновляем in-place
            seating.layout_json = layout
            seating.teacher_position = teacher_pos
        else:
            # Создаем с нуля
            seating = SeatingModel(
                class_id=class_id, layout_json=layout, teacher_position=teacher_pos
            )
            db.add(seating)

        await db.flush()
        return seating

    @staticmethod
    async def get_student_debts(db: AsyncSession, student_id: int) -> list[dict]:
        """
        Вытаскивает открытые задолженности текущего года (§4, §9.6)
        с передачей UUID урока для обеспечения сквозного Flow ученика из Miro.
        """
        current_year = UserRepository._get_current_academic_year()

        query = (
            select(DebtModel)
            .where(
                DebtModel.student_id == student_id,
                DebtModel.resolved == False,
                DebtModel.academic_year == current_year,
            )
            .options(selectinload(DebtModel.lesson).selectinload(LessonModel.subject))
        )
        result = await db.execute(query)
        debts = result.scalars().all()

        return [
            {
                "debt_id": debt.debt_id,
                "lesson_id": debt.lesson_id,  # СИНХРОНИЗАЦИЯ: отдаем UUID урока в схему ответа
                "type": debt.type if isinstance(debt.type, str) else debt.type.value,
                "resolved": debt.resolved,
                "lesson_date": (
                    debt.lesson.lesson_date if debt.lesson else datetime.date.today()
                ),
                "subject_name": (
                    debt.lesson.subject.name
                    if debt.lesson and debt.lesson.subject
                    else "Неизвестно"
                ),
                "topic_title": (
                    debt.lesson.homework if debt.lesson else "Тема не указана"
                ),  # вытаскиваем текст темы/ДЗ
            }
            for debt in debts
        ]

    @staticmethod
    async def publish_test_to_lesson(
        db: AsyncSession, test_id: int, lesson_id: uuid.UUID
    ) -> LessonModel | None:
        """
        Публикует тест, привязывая его к конкретному уроку по его UUID (§9.5).
        Переводит статус теста в 'published' и обновляет домашнее задание в кэше.
        """
        # 1. Проверяем существование теста и сразу подгружаем его объект
        test_query = select(TestModel).where(TestModel.test_id == test_id)
        test_result = await db.execute(test_query)
        test_obj = test_result.scalar_one_or_none()
        if not test_obj:
            return None

        # 2. Ищем нужный урок по его строгому типу UUID
        lesson_query = select(LessonModel).where(LessonModel.lesson_id == lesson_id)
        lesson_result = await db.execute(lesson_query)
        lesson = lesson_result.scalar_one_or_none()

        if lesson:
            test_obj.status = "published"
            test_obj.lesson_id = lesson_id  # Записываем физическую связь (Пункт 6 ТЗ)

            # 4. Модифицируем строку ДЗ, дописывая маркер ИИ-теста
            current_homework = lesson.homework if lesson.homework else ""
            prefix = "\n" if current_homework else ""
            lesson.homework = f"{current_homework}{prefix}[Пройти ИИ-тест №{test_id}]"

            # Выталкиваем изменения в текущую транзакцию СУБД
            await db.flush()

        return lesson

    @staticmethod
    async def get_user_by_vk_id(db: AsyncSession, vk_id: int) -> UserModel | None:
        """
        Ищет пользователя в базе данных по его единому цифровому vk_id Сферум/VK.
        """
        query = select(UserModel).where(UserModel.vk_id == vk_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_pending_user(
        db: AsyncSession, vk_id: int, full_name: str
    ) -> UserModel:
        """
        Автоматическая регистрация пользователя по vk_id из initData (§7.2, §8).
        """
        from scr.model.model import UserRole
        import random

        generated_id = random.randint(100000, 999999)

        # ХАКАТОН-ПРАВКА: Динамически определяем роль для демо-входа,
        # если сид базы данных был очищен или не успел отработать
        assigned_role = UserRole.TEACHER if vk_id == 12345 else UserRole.STUDENT

        new_user = UserModel(
            user_id=generated_id,
            vk_id=vk_id,
            full_name=full_name,
            role=assigned_role,  # Присваиваем корректную роль
            class_id=None,
            avatar_url="https://dicebear.com",
        )

        db.add(new_user)
        await db.flush()
        return new_user

    @staticmethod
    async def resolve_debt_manual(
        db: AsyncSession, debt_id: int, teacher_id: int
    ) -> dict:
        """
        Ручное закрытие долга учителем (PATCH /teacher/debts/{debt_id}) (§10.2).
        Реализует идемпотентность: если долг уже закрыт — пропускает операцию.
        """
        import datetime

        # Блокируем строку долга от конкурентных изменений со стороны синхронизации ЭЖД
        query = select(DebtModel).where(DebtModel.debt_id == debt_id).with_for_update()
        result = await db.execute(query)
        debt = result.scalar_one_or_none()

        if not debt:
            return {"status": "error", "message": "Задолженность не найдена"}

        # Идемпотентность: если resolved == True, повторное закрытие игнорируется
        if debt.resolved:
            return {"status": "skipped", "message": "already_resolved"}

        # Фиксируем закрытие долга
        debt.resolved = True
        debt.resolved_by = teacher_id
        debt.resolved_at = datetime.datetime.now(datetime.timezone.utc)

        await db.flush()
        return {"status": "success", "debt_id": debt_id}

    @staticmethod
    async def auto_resolve_debts_by_topic(
        db: AsyncSession, student_id: int, subject_id: int, normalized_topic: str
    ) -> int:
        """
        Автоматическое закрытие задолженностей при появлении выполненного ДЗ
        или оценки >= 3 по уроку с тем же topic_normalized (§10.2).
        Выполняется под SELECT FOR UPDATE. Возвращает количество закрытых долгов.
        """
        import datetime

        current_year = UserRepository._get_current_academic_year()

        # Ищем все открытые долги ученика по этому предмету и теме в текущем году
        query = (
            select(DebtModel)
            .where(
                DebtModel.student_id == student_id,
                DebtModel.subject_id == subject_id,
                DebtModel.topic_normalized == normalized_topic,
                DebtModel.resolved == False,
                DebtModel.academic_year == current_year,
            )
            .with_for_update()
        )

        result = await db.execute(query)
        open_debts = result.scalars().all()

        resolved_count = 0
        now = datetime.datetime.now(datetime.timezone.utc)

        for debt in open_debts:
            debt.resolved = True
            debt.resolved_at = now
            resolved_count += 1

        if resolved_count > 0:
            await db.flush()

        return resolved_count

    @staticmethod
    async def write_audit_log(
        db: AsyncSession,
        action: str,
        target_type: str,
        target_id: str,
        actor_id: int | None = None,
        external_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        """Запись действия пользователя в аудит-журнал (§13.4)"""
        from scr.model.model import AuditLogModel

        log_entry = AuditLogModel(
            actor_user_id=actor_id,
            actor_external_id=external_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            payload_json=payload,
        )
        db.add(log_entry)

    @staticmethod
    async def write_technical_log(
        db: AsyncSession,
        event: str,
        severity: str,
        context: dict | None = None,
        request_id: str | None = None,
    ) -> None:
        """Запись технического события без ПДн (§11.4)"""
        from scr.model.model import TechnicalLogModel

        log_entry = TechnicalLogModel(
            event=event, severity=severity, context_json=context, request_id=request_id
        )
        db.add(log_entry)
        await db.flush()

    @staticmethod
    async def write_sync_log(
        db: AsyncSession,
        entity: str,
        entity_id: str,
        status: str,
        payload: dict | None = None,
    ) -> None:
        """Запись события синхронизации ЭЖД (§11.4)"""
        from scr.model.model import SyncLogModel

        log_entry = SyncLogModel(
            entity=entity, entity_id=str(entity_id), status=status, payload_json=payload
        )
        db.add(log_entry)
        await db.flush()

    @staticmethod
    async def update_class_seating_photo(
        db: AsyncSession, class_id: int, filename: str
    ) -> SeatingModel | None:
        """
        Обновляет имя файла фотографии в таблице рассадки класса (§8).
        Удаляет предыдущий файл фотографии с диска, если он существовал.
        """

        query = select(SeatingModel).where(SeatingModel.class_id == class_id)
        result = await db.execute(query)
        seating = result.scalar_one_or_none()

        if not seating:
            return None

        # Если старый файл существовал — физически удаляем его по §9.9 ТЗ
        photos_dir = getattr(settings, "PHOTOS_DIR", "/tmp/photos")
        if seating.photo_filename:
            old_file_path = os.path.join(photos_dir, seating.photo_filename)
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception:
                    pass

        # Прописываем новое имя файла фотографии
        seating.photo_filename = filename
        await db.flush()
        return seating

    @staticmethod
    async def save_ejd_lessons_cache(db: AsyncSession, parsed_data: dict) -> None:
        """
        Массово сохраняет уроки и оценки из Excel-выгрузки ЕРИСО КО (§11.1.2).
        Реализует автозакрытие долгов при оценке >= 3 по каноничной теме (Страница 6 и 11 Контракта).
        """
        import datetime
        from sqlalchemy import select
        from scr.model.model import LessonModel, GradeModel, DebtModel, GradeSource
        from scr.services.text_service import TextNormalizationService

        current_year = UserRepository._get_current_academic_year()
        lessons_dtos = parsed_data.get("lessons", [])
        grades_dtos = parsed_data.get("grades", [])

        # --- 1. ОПТИМИЗАЦИЯ: Вытягиваем существующие уроки одним запросом ---
        lesson_ids = [dto.lesson_id for dto in lessons_dtos]
        existing_lessons_map = {}
        if lesson_ids:
            stmt = select(LessonModel).where(LessonModel.lesson_id.in_(lesson_ids))
            res = await db.execute(stmt)
            for row in res.scalars().all():
                existing_lessons_map[row.lesson_id] = row

        # --- 2. Сохранение / Обновление уроков in-place ---
        for dto in lessons_dtos:
            if dto.lesson_id in existing_lessons_map:
                # Обновляем тему/ДЗ на случай изменений без дублирования строк
                existing_lessons_map[dto.lesson_id].homework = dto.homework
            else:
                new_lesson = LessonModel(
                    lesson_id=dto.lesson_id,
                    class_id=dto.class_id,
                    subject_id=dto.subject_id,
                    teacher_id=dto.teacher_id,
                    lesson_date=dto.date,
                    lesson_number=dto.sequence,
                    homework=dto.homework,
                    academic_year=current_year,
                )
                db.add(new_lesson)

        # Выталкиваем уроки в транзакцию, чтобы на них могли сослаться оценки (FK)
        await db.flush()

        # --- 3. Сохранение оценок с точным разбором типа работы (Страница 9 и 11 Контракта) ---
        for g_dto in grades_dtos:
            db_source = GradeSource.MANUAL

            # Извлекаем тип работы из DTO (переданный из Excel адаптера: homework/control/vpr/regular)
            inferred_work_type = getattr(g_dto, "source", "regular")

            new_grade = GradeModel(
                lesson_id=g_dto.lesson_id,
                student_id=g_dto.student_id,
                value=g_dto.value,
                academic_year=current_year,
                work_type=inferred_work_type,  # Записываем реальный тип для стриков
                source=db_source,
            )
            db.add(new_grade)

            # --- 4. СКВОЗНОЙ БИЗНЕС-ЭФФЕКТ: Автозакрытие долгов (Страница 6, 11 Контракта) ---
            # Появление оценки 3 и выше автоматически закрывает долг
            if g_dto.value >= 3:
                now_utc = datetime.datetime.now(datetime.timezone.utc)

                # Попытка А: Ищем открытый долг по этому конкретному уроку
                debt_stmt = (
                    select(DebtModel)
                    .where(
                        DebtModel.student_id == g_dto.student_id,
                        DebtModel.lesson_id == g_dto.lesson_id,
                        DebtModel.resolved == False,
                    )
                    .with_for_update()  # Защита от конкурентной перезаписи в СУБД
                )
                debt_res = await db.execute(debt_stmt)
                active_debt = debt_res.scalar_one_or_none()

                if active_debt:
                    active_debt.resolved = True
                    active_debt.resolved_at = now_utc
                    active_debt.resolved_by = None
                else:
                    # Попытка Б (СИНХРОНИЗАЦИЯ ПО ТЕМЕ): Если по lesson_id долг не найден (например, новый синтетический UUID),
                    # ищем соответствующий урок в импортируемом пакете для нормализации названия темы
                    current_lesson_dto = next(
                        (l for l in lessons_dtos if l.lesson_id == g_dto.lesson_id),
                        None,
                    )

                    if current_lesson_dto and current_lesson_dto.topic:
                        # Канонизируем тему через сервис нормализации текста (ё->е, NFKC, удаление пунктуации)
                        normalized_topic = TextNormalizationService.topic_normalized(
                            current_lesson_dto.topic
                        )

                        # Закрываем все висящие долги по этой теме и предмету под SELECT FOR UPDATE
                        await UserRepository.auto_resolve_debts_by_topic(
                            db=db,
                            student_id=g_dto.student_id,
                            subject_id=current_lesson_dto.subject_id,
                            normalized_topic=normalized_topic,
                        )

        await db.flush()

    @staticmethod
    async def generate_ai_test(
        db: AsyncSession, topic: str, topic_id: int = 1, class_id: int | None = None,title: str = "Новый тест", question_count: int = 2, question_type: str | None = None
    ) -> TestModel:
        """
        Генерирует тест и привязывает его к конкретному классу.
        """
        from sqlalchemy import select, func
        from scr.model.model import StudyPlanModel, PlanTopicModel, SubjectModel, TestModel, TestQuestionModel, QuestionType, TestCreatedBy
        
        # 🔥 ШАГ 1: ПЕРЕПРИВЯЗЫВАЕМ ТЕМУ К НУЖНОМУ КЛАССУ (БЕЗ LAZY LOAD) 🔥
        if class_id and topic_id:
            # Узнаем subject_id текущей темы через JOIN
            subj_q = (
                select(StudyPlanModel.subject_id)
                .join(PlanTopicModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
                .where(PlanTopicModel.topic_id == topic_id)
                .limit(1)
            )
            subj_res = await db.execute(subj_q)
            subj_id = subj_res.scalar_one_or_none()

            if subj_id:
                # Ищем учебный план для класса, который выбрал учитель
                plan_q = select(StudyPlanModel).where(
                    StudyPlanModel.class_id == class_id,
                    StudyPlanModel.subject_id == subj_id
                )
                plan = (await db.execute(plan_q)).scalar_one_or_none()

                if plan:
                    # Достаем название темы
                    title_q = select(PlanTopicModel.title).where(PlanTopicModel.topic_id == topic_id)
                    title_res = await db.execute(title_q)
                    current_title = title_res.scalar_one_or_none()

                    if current_title:
                        # Ищем такую же тему в плане нужного класса
                        target_topic_q = select(PlanTopicModel).where(
                            PlanTopicModel.plan_id == plan.plan_id,
                            PlanTopicModel.title == current_title
                        )
                        target_topic = (await db.execute(target_topic_q)).scalar_one_or_none()

                        if target_topic:
                            topic_id = target_topic.topic_id # Перезаписываем ID на правильный
                        else:
                            # Если темы в плане этого класса нет, создаем её
                            max_order_q = select(func.max(PlanTopicModel.order_num)).where(PlanTopicModel.plan_id == plan.plan_id)
                            max_order = (await db.execute(max_order_q)).scalar() or 0

                            new_topic = PlanTopicModel(
                                plan_id=plan.plan_id,
                                order_num=max_order + 1,
                                title=current_title,
                                hours=1,
                                quarter=1,
                                is_current=False,
                                is_done=True
                            )
                            db.add(new_topic)
                            await db.flush()
                            topic_id = new_topic.topic_id

        # 🔥 ШАГ 2: СОЗДАЕМ ТЕСТ 🔥
        new_test = TestModel(topic_id=topic_id,title=title, created_by=TestCreatedBy.AI, status="draft")
        db.add(new_test)
        await db.flush()

        # 🔥 ШАГ 3: ДОСТАЕМ НАЗВАНИЕ ПРЕДМЕТА ДЛЯ ПРОМПТА 🔥
        subject_name = "Общий предмет"
        try:
            subj_name_q = (
                select(SubjectModel.name)
                .join(StudyPlanModel, SubjectModel.subject_id == StudyPlanModel.subject_id)
                .join(PlanTopicModel, StudyPlanModel.plan_id == PlanTopicModel.plan_id)
                .where(PlanTopicModel.topic_id == topic_id)
                .limit(1)
            )
            subj_name_res = await db.execute(subj_name_q)
            found_subj = subj_name_res.scalar_one_or_none()
            if found_subj:
                subject_name = found_subj
        except Exception:
            pass

        # 🔥 ШАГ 4: ГЕНЕРАЦИЯ ВОПРОСОВ (МОК ИЛИ ИИ) 🔥
        if settings.USE_MOCK_LLM:
            print(f"📦 [LLM-MOCK] Мок: {question_count} вопросов, тип: {question_type}, предмет: {subject_name}")
            for i in range(question_count):
                is_numeric = (question_type in ("numeric", "math")) or (question_type is None and i % 2 != 0)
                
                if is_numeric:
                    db.add(TestQuestionModel(
                        test_id=new_test.test_id, type=QuestionType.NUMERIC,
                        question=f"Практическое задание {i+1} по предмету {subject_name} (тема: {topic}).",
                        numeric_answer=0.0,
                    ))
                else:
                    db.add(TestQuestionModel(
                        test_id=new_test.test_id, type=QuestionType.CHOICE,
                        question=f"Тестовый вопрос {i+1} по предмету {subject_name} (тема: {topic}).",
                        options={"options": ["Вариант А", "Вариант Б", "Вариант В"]},
                        correct_option_index=0,
                    ))
        else:
            from scr.services.llm_service import YandexGPTService
            print(f"🤖 [LLM-LIVE] Запрос: {question_count} вопросов, тип: {question_type}, предмет: {subject_name}")
            
            ai_questions = await YandexGPTService.generate_questions_from_ai(
                topic, subject_name=subject_name, count=question_count, q_type=question_type
            )

            if ai_questions and isinstance(ai_questions, list):
                for ai_q in ai_questions:
                    q_type = ai_q.get("type", "choice")
                    
                    # 1. ЧИСЛОВЫЕ ОТВЕТЫ
                    if q_type == "numeric":
                        db.add(TestQuestionModel(
                            test_id=new_test.test_id, type=QuestionType.NUMERIC,
                            question=ai_q.get("question", "Решите задачу"),
                            numeric_answer=float(ai_q.get("numeric_answer", 0.0)),
                        ))
                    
                    # 2. СОПОСТАВЛЕНИЯ (НОВОЕ)
                    elif q_type == "matching":
                        options_dict = {
                            "left": ai_q.get("left", []),
                            "right": ai_q.get("right", []),
                            "correct_matches": ai_q.get("correct_matches", {})
                        }
                        db.add(TestQuestionModel(
                            test_id=new_test.test_id, type=QuestionType.MATCHING,
                            question=ai_q.get("question", "Сопоставьте элементы"),
                            options=options_dict,
                        ))
                        
                    # 3. ТЕСТОВЫЕ ВОПРОСЫ
                    else:
                        db.add(TestQuestionModel(
                            test_id=new_test.test_id, type=QuestionType.CHOICE,
                            question=ai_q.get("question", "Выберите ответ"),
                            options={"options": ai_q.get("options", ["А", "Б", "В"])},
                            correct_option_index=int(ai_q.get("correct_option_index", 0)),
                        ))
            else:
                # Если ИИ упал, делаем заглушку
                print("⚠️ [LLM-FALLBACK] Сбой LLM, откат на шаблон.")
                db.add(TestQuestionModel(
                    test_id=new_test.test_id, type=QuestionType.CHOICE,
                    question=f"Вопрос по теме «{topic}» (предмет: {subject_name}).",
                    options={"options": ["Да", "Нет", "Возможно"]}, correct_option_index=0,
                ))

        await db.flush()
        
        # Возвращаем готовый тест с вопросами
        query = select(TestModel).where(TestModel.test_id == new_test.test_id).options(selectinload(TestModel.questions))
        return (await db.execute(query)).scalar_one()

    @staticmethod
    def _get_current_academic_year() -> int:
        """
        Вспомогательный метод автоматического определения текущего учебного года (§4 ТЗ).
        Если текущий месяц с сентября по декабрь — год равен текущему.
        Если с января по август — год равен предыдущему.
        """
        today = datetime.date.today()
        return today.year if today.month >= 9 else today.year - 1

    @staticmethod
    async def get_seating_with_metadata(db: AsyncSession, class_id: int) -> dict | None:
        """
        Вытаскивает из СУБД схему рассадки класса, обогащая JSON-карту
        реальными именами (ФИО) учеников и текстовым названием класса для make_one.
        """

        # 1. Считываем базовую запись рассадки
        query = select(SeatingModel).where(SeatingModel.class_id == class_id)
        result = await db.execute(query)
        seating = result.scalar_one_or_none()
        if not seating:
            return None

        # 2. Вытаскиваем текстовое имя класса для красивого заголовка
        class_query = select(SchoolClassesModel.class_name).where(
            SchoolClassesModel.class_id == class_id
        )
        class_res = await db.execute(class_query)
        class_name = class_res.scalar_one_or_none() or "Класс"

        # 3. Собираем уникальные ID учеников, которые сейчас посажены в сетку
        layout = seating.layout_json.copy()
        seats = layout.get("seats", [])
        student_ids = [
            s.get("student_id") for s in seats if s.get("student_id") is not None
        ]

        # 4. Одним запросом вытаскиваем соответствие ID -> Имя (ФИО) из таблицы пользователей
        student_names_map = {}
        if student_ids:
            users_query = select(UserModel.user_id, UserModel.full_name).where(
                UserModel.user_id.in_(student_ids)
            )
            users_res = await db.execute(users_query)
            for uid, fname in users_res.all():
                # Превращаем "Иванов Иван Сергеевич" в компактное "Иванов И." для отрисовки на парте
                parts = fname.split()
                short_name = f"{parts[0]} {parts[1][0]}." if len(parts) >= 2 else fname
                student_names_map[uid] = short_name

        # 5. Обогащаем массив мест текстовыми именами для алгоритма Pillow
        for s in seats:
            sid = s.get("student_id")
            if sid in student_names_map:
                s["student_name"] = student_names_map[sid]

        return {
            "seating_id": seating.seating_id,
            "class_id": seating.class_id,
            "layout_json": layout,
            "teacher_position": seating.teacher_position,
            "photo_filename": seating.photo_filename,
            "class_name": class_name,
        }

    @staticmethod
    async def get_user_profile_with_subject(
        db: AsyncSession, user_id: int
    ) -> dict | None:
        """
        Вытаскивает данные профиля пользователя строго под контракт страницы 4.
        """
        query = select(UserModel).where(UserModel.user_id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        # Безопасно приводим Enum роли к строке
        role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        subject_data = None

        if role_str == "teacher":
            subject_query = (
                select(SubjectModel)
                .join(
                    ClassSubjectModel,
                    SubjectModel.subject_id == ClassSubjectModel.subject_id,
                )
                .where(ClassSubjectModel.teacher_id == user_id)
                .limit(1)
            )
            subj_res = await db.execute(subject_query)
            subject_obj = subj_res.scalar_one_or_none()
            if subject_obj:
                subject_data = {
                    "subject_id": subject_obj.subject_id,
                    "name": subject_obj.name,
                }

        return {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "role": role_str,
            "class_id": user.class_id,
            "subject": subject_data,  # Полное соответствие Pydantic-схеме UserMeResponse
        }

    @staticmethod
    async def get_teacher_dashboard_counters(db: AsyncSession, teacher_id: int) -> dict:
        """
        Полная агрегированная статистика для главного дашборда учителя (Страница 5 Контракта).
        B4: avg_score = None, если оценок нет (класс не считается проблемным по успеваемости).
        """
        from sqlalchemy import select, func
        from scr.model.model import (
            SchoolClassesModel,
            ClassSubjectModel,
            DebtModel,
            UserModel,
            LessonModel,
            GradeModel,
            TestModel,
            PlanTopicModel,
            StudyPlanModel,
        )

        current_year = UserRepository._get_current_academic_year()

        # 1. Все классы учителя
        classes_query = (
            select(SchoolClassesModel)
            .join(
                ClassSubjectModel,
                SchoolClassesModel.class_id == ClassSubjectModel.class_id,
            )
            .where(ClassSubjectModel.teacher_id == teacher_id)
            .distinct()
        )
        classes_res = await db.execute(classes_query)
        teacher_classes = classes_res.scalars().all()

        classes_metrics = []
        total_open_debts = 0
        worst_avg = 6.0
        problem_class_id = None

        # 2. Метрики по каждому классу
        for c in teacher_classes:
            # Долги класса
            debt_query = (
                select(func.count(DebtModel.debt_id))
                .join(UserModel, DebtModel.student_id == UserModel.user_id)
                .where(
                    UserModel.class_id == c.class_id,
                    DebtModel.resolved == False,
                    DebtModel.academic_year == current_year,
                )
            )
            debt_res = await db.execute(debt_query)
            debts_count = debt_res.scalar() or 0
            total_open_debts += debts_count

            # Средний балл класса
            grade_query = (
                select(func.avg(GradeModel.value))
                .join(UserModel, GradeModel.student_id == UserModel.user_id)
                .where(
                    UserModel.class_id == c.class_id,
                    GradeModel.academic_year == current_year,
                )
            )
            grade_res = await db.execute(grade_query)
            avg_score_raw = grade_res.scalar()
            # B4: None, если нет оценок
            avg_score = round(float(avg_score_raw), 1) if avg_score_raw else None

            # B4: None не считается проблемой по успеваемости
            is_problem = (
                (avg_score is not None and avg_score < 3.5) or debts_count > 3
            )

            classes_metrics.append(
                {
                    "class_id": c.class_id,
                    "class_name": c.class_name,
                    "avg_score": avg_score,
                    "debts_count": debts_count,
                    "is_problem": is_problem,
                }
            )

            # B4: None пропускаем при поиске проблемного класса
            if is_problem and avg_score is not None and avg_score < worst_avg:
                worst_avg = avg_score
                problem_class_id = c.class_id

        # Fallback: если по успеваемости никого, берём класс с максимумом долгов
        if not problem_class_id and classes_metrics:
            sorted_by_debts = sorted(
                classes_metrics, key=lambda x: x["debts_count"], reverse=True
            )
            if sorted_by_debts[0]["debts_count"] > 0:
                problem_class_id = sorted_by_debts[0]["class_id"]

        # 3. Темы на завтра
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        tomorrow_lessons_query = select(LessonModel).where(
            LessonModel.teacher_id == teacher_id, LessonModel.lesson_date == tomorrow
        )
        tomorrow_res = await db.execute(tomorrow_lessons_query)
        tomorrow_lessons = tomorrow_res.scalars().all()

        tomorrow_topics = (
            [
                {
                    "class_name": (
                        l.school_class.class_name if l.school_class else "Класс"
                    ),
                    "topic": l.homework or "Тема не указана",
                }
                for l in tomorrow_lessons
            ]
            if tomorrow_lessons
            else None
        )

        # 4. Список ИИ-тестов для панели «Тесты»
        class_ids = [c.class_id for c in teacher_classes]
        tests_list = []
        if class_ids:
            tests_query = (
                select(TestModel, PlanTopicModel.title, StudyPlanModel.class_id)
                .join(PlanTopicModel, TestModel.topic_id == PlanTopicModel.topic_id)
                .join(StudyPlanModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
                .where(StudyPlanModel.class_id.in_(class_ids),TestModel.status != "prep")
            )
            tests_res = await db.execute(tests_query)
            for t_obj, title, cid in tests_res.all():
                tests_list.append(
                    {
                        "test_id": t_obj.test_id,
                        "topic_id": t_obj.topic_id,
                        "topic_title": title,
                        "class_id": cid,
                        "title": t_obj.title,
                        "status": t_obj.status,
                        "lesson_id": t_obj.lesson_id,  
                    }
                )

        return {
            "classes": classes_metrics,
            "problem_class_id": problem_class_id,
            "metrics": {
                "total_open_debts": total_open_debts,
                "active_academic_year": current_year,
            },
            "tomorrow_topics": tomorrow_topics,
            "tests": tests_list,
        }

    @staticmethod
    async def get_class_students(db: AsyncSession, class_id: int) -> list[dict]:
        """
        Вытаскивает список всех учеников конкретного класса (Страница 6 Контракта).
        """
        from sqlalchemy import select
        from scr.model.model import UserModel, UserRole

        query = (
            select(UserModel)
            .where(UserModel.class_id == class_id, UserModel.role == UserRole.STUDENT)
            .order_by(UserModel.full_name.asc())
        )
        result = await db.execute(query)
        students = result.scalars().all()

        return [{"student_id": s.user_id, "full_name": s.full_name} for s in students]

    @staticmethod
    async def update_test_questions(
        db: AsyncSession, test_id: int, teacher_id: int, payload: "TestSaveRequest"
    ) -> TestModel | None:
        """Перезаписывает вопросы теста (для конструктора)."""
        from sqlalchemy import delete
        from scr.model.model import TestModel, TestQuestionModel, QuestionType
        
        # 1. Проверяем, что тест существует и он черновик
        test = await db.get(TestModel, test_id)
        if not test:
            return None
            
        if test.status != "draft":
            return None # Нельзя редактировать опубликованные

        # 2. Удаляем старые вопросы
        await db.execute(delete(TestQuestionModel).where(TestQuestionModel.test_id == test_id))

        # 3. Создаем новые
        for q in payload.questions:
            db_type = QuestionType.CHOICE
            correct_idx = q.correct_indices[0] if q.correct_indices else None
            num_ans = q.numeric_answer
            options_dict = None

            if q.type in ("math", "numeric"):
                db_type = QuestionType.NUMERIC
            elif q.type == "multiple_choice":
                options_dict = {
                    "options": q.options,
                    "is_multiple": True,
                    "correct_indices": q.correct_indices or []
                }
                correct_idx = None
            elif q.type == "text_input":
                correct_text = q.options[0] if q.options else ""
                options_dict = {
                    "options": q.options,
                    "is_text": True,
                    "correct_text": correct_text
                }
                correct_idx = None
            elif q.type == "matching":
                db_type = QuestionType.MATCHING
                options_dict = q.options
                correct_idx = None
            else:
                options_dict = {"options": q.options}

            db.add(TestQuestionModel(
                test_id=test_id,
                type=db_type,
                question=q.question,
                options=options_dict,
                correct_option_index=correct_idx,
                numeric_answer=num_ans,
                image_url=q.image_url
            ))
        
        if payload.topic_id and test.topic_id != payload.topic_id:
            test.topic_id = payload.topic_id
        if payload.title:
            test.title = payload.title   
        await db.flush()  
        return await UserRepository.get_test_with_questions(db, test_id)

    @staticmethod
    async def get_full_class_journal(
        db: AsyncSession,
        class_id: int,
        subject_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        Собирает полный контекст журнала успеваемости класса: список учеников,
        уроки со срезом пагинации и общее количество страниц total_pages (Страница 6 Контракта).
        """
        from sqlalchemy import select, func
        from scr.model.model import LessonModel

        current_year = UserRepository._get_current_academic_year()
        offset = (page - 1) * page_size

        # 1. Считаем общее число уроков для вычисления total_pages фронтенду
        count_query = select(func.count(LessonModel.lesson_id)).where(
            LessonModel.class_id == class_id,
            LessonModel.subject_id == subject_id,
            LessonModel.academic_year == current_year,
        )
        count_res = await db.execute(count_query)
        total_lessons = count_res.scalar() or 0
        total_pages = max(1, (total_lessons + page_size - 1) // page_size)

        # 2. Вытаскиваем пагинированные уроки
        lessons_query = (
            select(LessonModel)
            .where(
                LessonModel.class_id == class_id,
                LessonModel.subject_id == subject_id,
                LessonModel.academic_year == current_year,
            )
            .options(selectinload(LessonModel.grades), selectinload(LessonModel.topic))
            .order_by(LessonModel.lesson_date.desc(), LessonModel.lesson_number.asc())
            .limit(page_size)
            .offset(offset)
        )
        lessons_res = await db.execute(lessons_query)
        lessons = lessons_res.scalars().all()

        # 3. Получаем список студентов класса через наш метод
        students_list = await UserRepository.get_class_students(
            db=db, class_id=class_id
        )

        # 4. Форматируем уроки в понятную Pydantic-схеме структуру
        formatted_lessons = [
            {
                "lesson_id": lesson.lesson_id,
                "lesson_date": lesson.lesson_date,
                "lesson_number": lesson.lesson_number,
                "topic_title": (
                    lesson.topic.title
                    if lesson.topic
                    else (lesson.homework or "Тема не указана")
                ),
                "homework": lesson.homework,
                "grades": [
                    {"student_id": grade.student_id, "value": grade.value}
                    for grade in lesson.grades
                ],
            }
            for lesson in lessons
        ]

        return {
            "students": students_list,
            "lessons": formatted_lessons,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    async def get_student_dashboard_data(db: AsyncSession, student_id: int) -> dict:
        """
        Собирает полный контекст главного экрана ученика (Страница 9 Контракта).
        Рассчитывает предметы, лучший стрик, долги и доступные тесты с лимитом в 3 попытки.
        """
        from sqlalchemy import select, func
        from scr.model.model import (
            UserModel,
            SubjectModel,
            ClassSubjectModel,
            StreakModel,
            DebtModel,
            TestModel,
            LessonModel,  # ДОБАВЛЕНО: без этого импорта упадет запрос на шаге 5!
            TestAttemptModel,
        )

        current_year = UserRepository._get_current_academic_year()

        # 1. Извлекаем данные ученика для определения его класса
        user_query = select(UserModel.class_id).where(UserModel.user_id == student_id)
        user_res = await db.execute(user_query)
        class_id = user_res.scalar_one_or_none()

        subjects_list = []
        streak_val = 0
        debts_count = 0
        available_tests = []

        if class_id:
            # 2. Вытаскиваем список всех предметов класса
            sub_query = (
                select(SubjectModel)
                .join(
                    ClassSubjectModel,
                    SubjectModel.subject_id == ClassSubjectModel.subject_id,
                )
                .where(ClassSubjectModel.class_id == class_id)
                .distinct()
            )
            sub_res = await db.execute(sub_query)
            subjects_list = [
                {"subject_id": s.subject_id, "name": s.name}
                for s in sub_res.scalars().all()
            ]

            # 3. Вычисляем лучший (максимальный) стрик по всем предметам («Огонёк»)
            streak_query = select(func.max(StreakModel.current_streak)).where(
                StreakModel.student_id == student_id,
                StreakModel.academic_year == current_year,
            )
            streak_res = await db.execute(streak_query)
            streak_val = streak_res.scalar() or 0

            # 4. Считаем количество открытых долгов ученика в текущем году
            debt_query = select(func.count(DebtModel.debt_id)).where(
                DebtModel.student_id == student_id,
                DebtModel.resolved == False,
                DebtModel.academic_year == current_year,
            )
            debt_res = await db.execute(debt_query)
            debts_count = debt_res.scalar() or 0

            # 5. Собираем опубликованные тесты для класса ученика, привязанные через lesson_id
            tests_query = (
                select(TestModel, LessonModel.homework, SubjectModel.name)
                .join(LessonModel, TestModel.lesson_id == LessonModel.lesson_id)
                .join(SubjectModel, LessonModel.subject_id == SubjectModel.subject_id)
                .where(
                    LessonModel.class_id == class_id, TestModel.status == "published"
                )
            )
            tests_res = await db.execute(tests_query)

            for test, lesson_homework, subj_name in tests_res.all():
                attempts_query = select(TestAttemptModel.score).where(
                    TestAttemptModel.test_id == test.test_id,
                    TestAttemptModel.student_id == student_id,
                )
                attempts_res = await db.execute(attempts_query)
                scores = [int(s) for s in attempts_res.scalars().all() if s is not None]

                attempts_used = len(scores)
                attempts_left = max(0, 3 - attempts_used)
                best_percent = max(scores) if scores else None

                # Извлекаем красивое название темы из текста ДЗ (отсекая маркер теста)
                topic_title = (
                    lesson_homework.split("\n")[0]
                    if lesson_homework
                    else "Тема не указана"
                )

                available_tests.append(
                    {
                        "test_id": test.test_id,
                        "topic_title": topic_title,
                        "subject_name": subj_name,
                        "attempts_used": attempts_used,
                        "attempts_left": attempts_left,
                        "best_percent": best_percent,
                    }
                )

        return {
            "subjects": subjects_list,
            "streak": {"current_streak": streak_val},
            "debts_count": debts_count,
            "available_tests": available_tests,
        }

    @staticmethod
    async def get_filtered_student_grades(
        db: AsyncSession, student_id: int, subject_id: int
    ) -> dict | None:
        """
        Отчёт по оценкам ученика с фильтрацией по предмету (Страница 9 Контракта).
        B4: avg_score = None, если оценок нет.
        """
        from sqlalchemy import select
        from scr.model.model import GradeModel, LessonModel, SubjectModel

        current_year = UserRepository._get_current_academic_year()

        sub_query = select(SubjectModel).where(SubjectModel.subject_id == subject_id)
        sub_res = await db.execute(sub_query)
        subject_obj = sub_res.scalar_one_or_none()
        if not subject_obj:
            return None

        query = (
            select(GradeModel)
            .join(LessonModel, GradeModel.lesson_id == LessonModel.lesson_id)
            .where(
                GradeModel.student_id == student_id,
                LessonModel.subject_id == subject_id,
                GradeModel.academic_year == current_year,
            )
            .options(selectinload(GradeModel.lesson).selectinload(LessonModel.topic))
            .order_by(LessonModel.lesson_date.desc())
        )
        result = await db.execute(query)
        grades = result.scalars().all()

        total_score = 0
        homework_total = 0
        homework_done = 0
        formatted_grades = []

        for g in grades:
            total_score += g.value

            is_hw = g.lesson.homework is not None if g.lesson else False
            work_type = "homework" if is_hw else "regular"

            if work_type == "homework":
                homework_total += 1
                if g.value >= 3:
                    homework_done += 1

            topic_title = "Тема не указана"
            if g.lesson:
                if g.lesson.topic:
                    topic_title = g.lesson.topic.title
                elif g.lesson.homework:
                    topic_title = g.lesson.homework

            formatted_grades.append(
                {
                    "grade_id": g.grade_id,
                    "value": g.value,
                    "lesson_date": (
                        g.lesson.lesson_date if g.lesson else datetime.date.today()
                    ),
                    "topic_title": topic_title,
                    "work_type": work_type,
                }
            )

        count = len(grades)
        # B4: None, если оценок нет (фронт рисует «—»)
        avg_score = round(total_score / count, 1) if count > 0 else None

        hw_percent = (
            int((homework_done / homework_total) * 100) if homework_total > 0 else 0
        )

        return {
            "subject": {"subject_id": subject_obj.subject_id, "name": subject_obj.name},
            "avg_score": avg_score,
            "homework_percent": hw_percent,
            "grades": formatted_grades,
        }

    @staticmethod
    async def get_class_analytics_data(
        db: AsyncSession,
        class_id: int,
        teacher_id: int,
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> dict | None:
        """
        Аналитика класса по предмету (Страница 5-6 Контракта).
        B3: рекомендация с цифрами (mastery_percent, students_with_gaps).
        B4: avg_score = None, если оценок нет.
        ВНИМАНИЕ: Здесь больше нет вызова ИИ (LLM), только быстрая статистика!
        """
        from sqlalchemy import select, func, case
        from scr.model.model import (
            ClassSubjectModel,
            GradeModel,
            LessonModel,
            UserModel,
            DebtModel,
            PlanTopicModel,
        )

        current_year = UserRepository._get_current_academic_year()

        # 0. Предмет учителя
        subj_stmt = (
            select(ClassSubjectModel.subject_id)
            .where(ClassSubjectModel.teacher_id == teacher_id)
            .limit(1)
        )
        subj_res = await db.execute(subj_stmt)
        subject_id = subj_res.scalar_one_or_none()
        if not subject_id:
            return None

        # 1. Активные долги
        total_debts_stmt = (
            select(func.count(DebtModel.debt_id))
            .join(UserModel, DebtModel.student_id == UserModel.user_id)
            .where(
                UserModel.class_id == class_id,
                DebtModel.resolved == False,
                DebtModel.academic_year == current_year,
            )
        )
        total_debts_res = await db.execute(total_debts_stmt)
        active_debts = total_debts_res.scalar() or 0

        # 2. Средний балл (B4: None, если данных нет)
        total_avg_stmt = (
            select(func.avg(GradeModel.value))
            .join(UserModel, GradeModel.student_id == UserModel.user_id)
            .join(LessonModel, GradeModel.lesson_id == LessonModel.lesson_id)
            .where(
                UserModel.class_id == class_id,
                LessonModel.subject_id == subject_id,
                GradeModel.academic_year == current_year,
            )
        )
        total_avg_res = await db.execute(total_avg_stmt)
        total_avg_raw = total_avg_res.scalar()
        class_avg_score = round(float(total_avg_raw), 1) if total_avg_raw else None

        # 3. Распределение оценок
        dist_stmt = (
            select(GradeModel.value, func.count(GradeModel.grade_id))
            .join(UserModel, GradeModel.student_id == UserModel.user_id)
            .join(LessonModel, GradeModel.lesson_id == LessonModel.lesson_id)
            .where(
                UserModel.class_id == class_id,
                LessonModel.subject_id == subject_id,
                LessonModel.lesson_date >= date_from,
                LessonModel.lesson_date <= date_to,
            )
            .group_by(GradeModel.value)
        )
        dist_res = await db.execute(dist_stmt)
        dist_map = {5: 0, 4: 0, 3: 0, 2: 0}
        for val, count in dist_res.all():
            if val in dist_map:
                dist_map[val] = count

        # 4. Карта пробелов с метриками (B3)
        topics_stmt = (
            select(
                func.coalesce(PlanTopicModel.title, LessonModel.homework).label("title"),
                func.avg(GradeModel.value).label("avg_score"),
                func.count(GradeModel.grade_id).label("grades_count"),
                func.count(
                    func.distinct(
                        case((GradeModel.value < 3, GradeModel.student_id), else_=None)
                    )
                ).label("students_with_gaps"),
                func.sum(case((GradeModel.value >= 4, 1), else_=0)).label("mastery_count"),
            )
            .select_from(LessonModel)
            .join(GradeModel, LessonModel.lesson_id == GradeModel.lesson_id)
            .join(UserModel, GradeModel.student_id == UserModel.user_id)
            .outerjoin(PlanTopicModel, PlanTopicModel.topic_id == LessonModel.topic_id)
            .where(
                UserModel.class_id == class_id,
                LessonModel.subject_id == subject_id,
                LessonModel.lesson_date >= date_from,
                LessonModel.lesson_date <= date_to,
                func.coalesce(PlanTopicModel.title, LessonModel.homework).is_not(None),
            )
            .group_by(func.coalesce(PlanTopicModel.title, LessonModel.homework))
            .order_by(func.max(LessonModel.lesson_date).desc())
            .limit(7)
        )
        topics_res = await db.execute(topics_stmt)

        topics_avg_list = []
        weakest_topic = None
        lowest_score = 6.0
        virtual_id = 100

        for title, t_avg, grades_count, students_with_gaps, mastery_count in topics_res.all():
            if "[пройти ии тест" in title.lower():
                title = title.split("\n")[0]

            score = round(float(t_avg), 1) if t_avg else 0.0
            mastery_percent = (
                round(100 * int(mastery_count) / int(grades_count))
                if grades_count
                else 0
            )

            topic_data = {
                "topic_id": virtual_id,
                "topic_title": title,
                "avg_score": score,
                "grades_count": int(grades_count or 0),
                "mastery_percent": mastery_percent,
                "students_with_gaps": int(students_with_gaps or 0),
            }
            topics_avg_list.append(topic_data)
            virtual_id += 1

            if score > 0.0 and score < lowest_score:
                lowest_score = score
                weakest_topic = topic_data

        # 5. БЫСТРАЯ рекомендация-заглушка (без вызова ИИ)
        if weakest_topic:
            ai_recommendation = (
                f"Тема «{weakest_topic['topic_title']}» требует внимания. "
                f"Усвоили {weakest_topic['mastery_percent']}% класса "
                f"(средний балл {weakest_topic['avg_score']}), "
                f"у {weakest_topic['students_with_gaps']} учеников пробелы."
            )
        else:
            ai_recommendation = None

        return {
            "class_id": class_id,
            "period": {"date_from": date_from, "date_to": date_to},
            "big_numbers": {"avg_score": class_avg_score, "active_debts": active_debts},
            "grade_distribution": {
                "grade_5": dist_map[5],
                "grade_4": dist_map[4],
                "grade_3": dist_map[3],
                "grade_2": dist_map[2],
            },
            "topics_avg": topics_avg_list,
            "weakest_topic": weakest_topic,
            "ai_recommendation": ai_recommendation,
        }
    @staticmethod
    async def get_topics_by_subject(db: AsyncSession, subject_id: int) -> list[dict]:
        """
        Вытаскивает из СУБД список всех уникальных тем по предмету (Страница 7 Контракта).
        """
        from sqlalchemy import select
        from scr.model.model import PlanTopicModel, StudyPlanModel

        query = (
            select(PlanTopicModel.topic_id, PlanTopicModel.title)
            .join(StudyPlanModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
            .where(StudyPlanModel.subject_id == subject_id)
            .order_by(PlanTopicModel.order_num.asc())
        )
        result = await db.execute(query)

        return [
            {"topic_id": row.topic_id, "topic_title": row.title} for row in result.all()
        ]

    @staticmethod
    async def delete_test(db: AsyncSession, test_id: int, teacher_id: int) -> bool:
        """Удаляет тест (и каскадно все вопросы/попытки), если он принадлежит учителю."""
        from scr.model.model import TestModel, StudyPlanModel, PlanTopicModel
        
        test = await db.get(TestModel, test_id)
        if not test:
            return False
            
        owner_q = select(StudyPlanModel.teacher_id).join(
            PlanTopicModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id
        ).where(PlanTopicModel.topic_id == test.topic_id)
        
        owner_id = (await db.execute(owner_q)).scalar_one_or_none()
        if owner_id != teacher_id:
            return False
            
        await db.delete(test)
        await db.flush()
        return True

    @staticmethod
    async def get_topics_by_teacher_subject(
        db: AsyncSession, teacher_id: int
    ) -> list[dict]:
        """
        Находит предмет учителя и возвращает УНИКАЛЬНЫЕ темы для генератора тестов.
        """
        from sqlalchemy import select
        from scr.model.model import PlanTopicModel, StudyPlanModel, ClassSubjectModel

        # 1. Сначала находим предмет, закрепленный за учителем
        subj_query = (
            select(ClassSubjectModel.subject_id)
            .where(ClassSubjectModel.teacher_id == teacher_id)
            .limit(1)
        )
        subj_res = await db.execute(subj_query)
        subject_id = subj_res.scalar_one_or_none()

        if not subject_id:
            return []

        # 2. Вытаскиваем темы по найденному предмету
        query = (
            select(PlanTopicModel.topic_id, PlanTopicModel.title, PlanTopicModel.order_num)
            .join(StudyPlanModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
            .where(StudyPlanModel.subject_id == subject_id)
            .order_by(PlanTopicModel.order_num.asc())
        )
        result = await db.execute(query)

        # 3. Дедупликация: оставляем только уникальные названия тем
        unique_topics = {}
        for row in result.all():
            if row.title not in unique_topics:
                unique_topics[row.title] = row.topic_id

        return [
            {"topic_id": tid, "topic_title": title} for title, tid in unique_topics.items()
        ]
    @staticmethod
    async def get_topic_title_for_teacher(
        db: AsyncSession, topic_id: int, teacher_id: int
    ) -> str | None:
        """
        Возвращает PlanTopicModel.title по topic_id, если тема принадлежит
        предмету, который ведёт teacher_id. Иначе None.
        """
        from scr.model.model import (
            ClassSubjectModel,
            StudyPlanModel,
            PlanTopicModel,
        )

        subj_q = (
            select(ClassSubjectModel.subject_id)
            .where(ClassSubjectModel.teacher_id == teacher_id)
            .limit(1)
        )
        subj_res = await db.execute(subj_q)
        subject_id = subj_res.scalar_one_or_none()
        if not subject_id:
            return None

        q = (
            select(PlanTopicModel.title)
            .join(StudyPlanModel, PlanTopicModel.plan_id == StudyPlanModel.plan_id)
            .where(
                PlanTopicModel.topic_id == topic_id,
                StudyPlanModel.subject_id == subject_id,
            )
            .limit(1)
        )
        res = await db.execute(q)
        return res.scalar_one_or_none()
    @staticmethod
    async def generate_smart_seating(
        db: AsyncSession, class_id: int, teacher_id: int, cols: int = 6
    ) -> dict | None:
        """
        Умная рассадка:
        1. Ученики с плохим зрением (front_row) и слухом (acoustic) садятся ПЕРВЫМИ на первые парты.
        2. Ученики с плохим поведением (separation) рассаживаются по одному.
        3. Остальные заполняют места.
        """
        from sqlalchemy import select
        import random
        from scr.model.model import UserModel, UserRole, StudentMarkerModel, ClassSubjectModel

        # 1. Проверка прав учителя
        check_stmt = select(ClassSubjectModel).where(
            ClassSubjectModel.class_id == class_id,
            ClassSubjectModel.teacher_id == teacher_id,
        ).limit(1)
        if not (await db.execute(check_stmt)).scalar_one_or_none():
            return None

        # 2. Загрузка студентов и маркеров
        students_stmt = select(UserModel).where(
            UserModel.class_id == class_id, UserModel.role == UserRole.STUDENT
        )
        students = (await db.execute(students_stmt)).scalars().all()
        if not students:
            return {"empty": True}

        markers_stmt = select(StudentMarkerModel).where(StudentMarkerModel.class_id == class_id)
        student_markers_map = {}
        for m in (await db.execute(markers_stmt)).scalars().all():
            marker_str = "separation_required" if m.marker.value == "separation_requered" else m.marker.value
            student_markers_map.setdefault(m.student_id, []).append(marker_str)

        # 3. Делим учеников на 3 группы (СНАЧАЛА проверяем зрение/слух!)
        front_row_students = []
        separation_students = []
        regular_students = []
        separation_ids = set()

        for s in students:
            markers = student_markers_map.get(s.user_id, [])
            if "front_row_preference" in markers or "acoustic_preference" in markers:
                front_row_students.append(s)
            elif "separation_required" in markers:
                separation_students.append(s)
                separation_ids.add(s.user_id)
            else:
                regular_students.append(s)

        random.shuffle(front_row_students)
        random.shuffle(separation_students)
        random.shuffle(regular_students)

        # 4. Размер сетки
        rows = max(5, (len(students) + cols - 1) // cols)
        grid = [[None for _ in range(cols)] for _ in range(rows)]

        def is_separation_neighbor(r, c):
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    neighbor = grid[nr][nc]
                    if neighbor and neighbor.user_id in separation_ids:
                        return True
            return False

        # 6. ШАГ 1: Сажаем приоритетных (зрение/слух) САМЫМИ ПЕРВЫМИ
        for student in front_row_students:
            placed = False
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] is None:
                        grid[r][c] = student
                        placed = True
                        break
                if placed: break

        # 7. ШАГ 2: Сажаем "проблемных"
        for student in separation_students:
            placed = False
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] is None and not is_separation_neighbor(r, c):
                        grid[r][c] = student
                        placed = True
                        break
                if placed: break
            
            if not placed:
                for r in range(rows):
                    for c in range(cols):
                        if grid[r][c] is None:
                            grid[r][c] = student
                            placed = True
                            break
                    if placed: break

        # 8. ШАГ 3: Обычные ученики
        for student in regular_students:
            placed = False
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] is None:
                        grid[r][c] = student
                        placed = True
                        break
                if placed: break

        # 9. Формируем JSON
        FRONTEND_MARKER_MAP = {
            "front_row_preference": "vision",
            "acoustic_preference": "hearing",
            "separation_requered": "behavior",
            "separation_required": "behavior",
        }

        layout_seats = []
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] is not None:
                    s = grid[r][c]
                    raw_markers = student_markers_map.get(s.user_id, [])
                    front_markers = [FRONTEND_MARKER_MAP.get(m, m) for m in raw_markers]
                    layout_seats.append({
                        "row": r,
                        "col": c,
                        "student_id": s.user_id,
                        "student_name": s.full_name,
                        "markers": front_markers
                    })

        return {
            "class_id": class_id,
            "layout_json": {
                "grid": {"rows": rows, "cols": cols},
                "seats": layout_seats,
                "teacher": {"row": 0, "col": 2},
                "conflicts": [],
                "excluded_student_ids": [],
            },
            "teacher_position": "front_center",
            "photo_url": None,
        }
    @staticmethod
    async def get_parallel_rating(
        db: AsyncSession, student_id: int, event_type: str
    ) -> dict | None:
        """
        Собирает рейтинг классов параллели по типу события (exam или vpr) (Страница 10 Контракта).
        Использует ID ученика для автоматического определения его параллели и my_class_id.
        """
        from sqlalchemy import select, desc
        from scr.model.model import (
            UserModel,
            SchoolClassesModel,
            ClassRatingModel,
            ClassRatingEventType,
        )

        # 1. С помощью current_user определяем class_id и параллель текущего ученика
        user_stmt = (
            select(UserModel.class_id, SchoolClassesModel.parallel)
            .join(SchoolClassesModel, UserModel.class_id == SchoolClassesModel.class_id)
            .where(UserModel.user_id == student_id)
        )
        user_res = await db.execute(user_stmt)
        user_info = user_res.first()

        if not user_info or user_info.class_id is None:
            return None  # Ученик не привязан к классу

        my_class_id, my_parallel = user_info.class_id, user_info.parallel

        # Преобразуем строковый параметр в Enum СУБД
        try:
            db_event_type = ClassRatingEventType(event_type)
        except ValueError:
            return None

        # 2. Вытягиваем средние баллы классов той же параллели за текущие события
        rating_stmt = (
            select(
                SchoolClassesModel.class_id,
                SchoolClassesModel.class_name,
                ClassRatingModel.avg_score,
            )
            .join(
                ClassRatingModel,
                SchoolClassesModel.class_id == ClassRatingModel.class_id,
            )
            .where(
                SchoolClassesModel.parallel == my_parallel,
                ClassRatingModel.event_type == db_event_type,
            )
            .order_by(desc(ClassRatingModel.avg_score))
        )
        rating_res = await db.execute(rating_stmt)
        rows = rating_res.all()

        # 3. Формируем ранжированный список с местами (place) от 1 до N
        rating_items = []
        for idx, row in enumerate(rows, start=1):
            rating_items.append(
                {
                    "place": idx,
                    "class_id": row.class_id,
                    "class_name": row.class_name,
                    "avg_score": float(row.avg_score),
                }
            )

        return {"type": event_type, "items": rating_items, "my_class_id": my_class_id}
    @staticmethod
    async def generate_ai_recommendation(
        db: AsyncSession, 
        class_id: int, 
        teacher_id: int, 
        date_from: datetime.date, 
        date_to: datetime.date
    ) -> str | None:
        """
        Отдельный медленный метод для генерации рекомендации через ИИ.
        Вызывается из отдельной ручки, чтобы не блокировать загрузку основной аналитики.
        """
        # Импортируем здесь, чтобы избежать циклических зависимостей
        from scr.services.llm_service import YandexGPTService
        from scr.config import settings

        # 1. Получаем быструю статистику из БД (ту самую, что мы только что оптимизировали)
        analytics = await UserRepository.get_class_analytics_data(
            db=db, class_id=class_id, teacher_id=teacher_id, date_from=date_from, date_to=date_to
        )
        
        if not analytics or not analytics.get("weakest_topic"):
            return None

        weakest = analytics["weakest_topic"]
        
        # 2. Если включен мок (заглушка), возвращаем текст, который сгенерировал get_class_analytics_data
        if settings.USE_MOCK_LLM:
            return analytics.get("ai_recommendation")

        # 3. Идем в реальный ИИ
        prompt = (
            f"Напиши короткую рекомендацию для учителя (1-2 предложения). "
            f"В классе {weakest['mastery_percent']}% учеников усвоили тему "
            f"«{weakest['topic_title']}». У {weakest['students_with_gaps']} учеников есть пробелы. "
            f"Дай конкретный совет, как улучшить ситуацию."
        )
        
        try:
            ai_res = await YandexGPTService.generate_text(prompt)
            # Если ИИ вернул текст — отдаем его. Если нет — откатываемся на шаблон.
            return ai_res if ai_res else analytics.get("ai_recommendation")
        except Exception as e:
            print(f"⚠️ Ошибка генерации рекомендации: {e}")
            return analytics.get("ai_recommendation")
