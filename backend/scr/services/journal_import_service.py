"""
Запись разобранной выгрузки ЕРИСО КО в БД: темы, уроки, оценки, долги, стрики.
"""
import datetime
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from scr.model.model import (
    ClassSubjectModel,
    DebtModel,
    DebtType,
    GradeModel,
    GradeSource,
    LessonModel,
    PlanTopicModel,
    SchoolClassesModel,
    StreakModel,
    StudyPlanModel,
    StudyPlanStatus,
    SubjectModel,
    UserModel,
    UserRole,
)
from scr.services.journal_excel_service import (
    MAX_ERRORS,
    academic_year_for,
    build_student_index,
    normalize_class_name,
    normalize_text,
    quarter_for,
    resolve_rows,
    synthetic_lesson_id,
)


async def _sync_sequence(db: AsyncSession, model, column: str) -> None:
    table = model.__tablename__
    await db.execute(text(
        f"SELECT setval(pg_get_serial_sequence('\"{table}\"', '{column}'), "
        f"COALESCE((SELECT MAX({column}) FROM \"{table}\"), 1))"
    ))


class JournalImportService:
    @staticmethod
    async def import_rows(db: AsyncSession, teacher_id: int, school_id: int, rows: list) -> dict:
        assignments, class_ids = await JournalImportService._load_assignments(db, teacher_id)
        students = await JournalImportService._load_students(db, class_ids)
        result = resolve_rows(rows, assignments, students)

        topic_ids, topics_created = await JournalImportService._ensure_topics(db, teacher_id, result.lessons)
        (lesson_ids, lessons_created, lessons_updated) = await JournalImportService._upsert_lessons(
            db, teacher_id, school_id, result.lessons, topic_ids
        )
        
        grades_created, grades_updated, affected_streaks = await JournalImportService._upsert_grades(
            db, result, lesson_ids
        )
        
        # B2: Пересчёт стриков после импорта
        if affected_streaks:
            await JournalImportService._update_streaks(db, affected_streaks)
            
        await db.flush()

        return {
            "lessons_processed": lessons_created + lessons_updated,
            "lessons_created": lessons_created,
            "lessons_updated": lessons_updated,
            "topics_created": topics_created,
            "grades_processed": grades_created + grades_updated,
            "grades_created": grades_created,
            "grades_updated": grades_updated,
            "skipped_rows": result.skipped_rows,
            "errors": result.errors[:MAX_ERRORS],
            "class_ids": sorted({spec.class_id for spec in result.lessons.values()}),
        }

    @staticmethod
    async def _load_assignments(db: AsyncSession, teacher_id: int):
        stmt = (
            select(ClassSubjectModel.class_id, ClassSubjectModel.subject_id, SchoolClassesModel.class_name, SubjectModel.name)
            .join(SchoolClassesModel, SchoolClassesModel.class_id == ClassSubjectModel.class_id)
            .join(SubjectModel, SubjectModel.subject_id == ClassSubjectModel.subject_id)
            .where(ClassSubjectModel.teacher_id == teacher_id)
        )
        assignments: dict = {}
        class_ids: set = set()
        for class_id, subject_id, class_name, subject_name in (await db.execute(stmt)).all():
            pair = (normalize_class_name(class_name), normalize_text(subject_name))
            assignments[pair] = (class_id, subject_id)
            class_ids.add(class_id)
        return assignments, class_ids

    @staticmethod
    async def _load_students(db: AsyncSession, class_ids: set):
        if not class_ids: return {}
        stmt = select(UserModel.user_id, UserModel.full_name, UserModel.class_id).where(
            UserModel.class_id.in_(class_ids), UserModel.role == UserRole.STUDENT
        )
        return build_student_index((await db.execute(stmt)).all())

    @staticmethod
    async def _ensure_topics(db: AsyncSession, teacher_id: int, lessons: dict):
        needed: dict = {}
        for (class_id, subject_id, _date, topic_norm), spec in lessons.items():
            if not topic_norm or not spec.topic: continue
            bucket = needed.setdefault((class_id, subject_id), {})
            known = bucket.get(topic_norm)
            if known is None or spec.lesson_date < known[1]:
                bucket[topic_norm] = (spec.topic, spec.lesson_date)
        if not needed: return {}, 0

        plan_stmt = select(StudyPlanModel.plan_id, StudyPlanModel.class_id, StudyPlanModel.subject_id).where(
            StudyPlanModel.teacher_id == teacher_id, StudyPlanModel.class_id.in_({c for c, _ in needed})
        )
        plans: dict = {}
        for plan_id, class_id, subject_id in (await db.execute(plan_stmt)).all():
            key = (class_id, subject_id)
            if key in needed and (key not in plans or plan_id < plans[key]):
                plans[key] = plan_id

        missing_plans = [key for key in needed if key not in plans]
        if missing_plans:
            await _sync_sequence(db, StudyPlanModel, "plan_id")
            created = {}
            for class_id, subject_id in missing_plans:
                plan = StudyPlanModel(class_id=class_id, subject_id=subject_id, teacher_id=teacher_id, status=StudyPlanStatus.ACTIVE)
                db.add(plan)
                created[(class_id, subject_id)] = plan
            await db.flush()
            for key, plan in created.items():
                plans[key] = plan.plan_id

        topic_stmt = select(PlanTopicModel.topic_id, PlanTopicModel.plan_id, PlanTopicModel.title, PlanTopicModel.order_num).where(
            PlanTopicModel.plan_id.in_(set(plans.values()))
        )
        by_plan_title: dict = {}
        max_order: dict = {}
        for topic_id, plan_id, title, order_num in (await db.execute(topic_stmt)).all():
            by_plan_title[(plan_id, normalize_text(title))] = topic_id
            max_order[plan_id] = max(max_order.get(plan_id, 0), order_num)

        topic_ids: dict = {}
        new_topics: list = []
        for (class_id, subject_id), bucket in needed.items():
            plan_id = plans[(class_id, subject_id)]
            for topic_norm, (title, first_date) in sorted(bucket.items(), key=lambda item: item[1][1]):
                existing = by_plan_title.get((plan_id, topic_norm))
                if existing is not None:
                    topic_ids[(class_id, subject_id, topic_norm)] = existing
                    continue
                max_order[plan_id] = max_order.get(plan_id, 0) + 1
                topic = PlanTopicModel(
                    plan_id=plan_id, order_num=max_order[plan_id], title=title[:255], hours=1,
                    quarter=quarter_for(first_date), is_current=False, is_done=True,
                )
                new_topics.append(((class_id, subject_id, topic_norm), topic))

        if new_topics:
            await _sync_sequence(db, PlanTopicModel, "topic_id")
            db.add_all([topic for _, topic in new_topics])
            await db.flush()
            for key, topic in new_topics:
                topic_ids[key] = topic.topic_id
        return topic_ids, len(new_topics)

    @staticmethod
    async def _upsert_lessons(db: AsyncSession, teacher_id: int, school_id: int, lessons: dict, topic_ids: dict):
        lesson_ids = {
            key: synthetic_lesson_id(school_id, spec.class_id, spec.subject_id, spec.lesson_date, spec.sequence)
            for key, spec in lessons.items()
        }
        if not lesson_ids: return {}, 0, 0

        existing_stmt = select(LessonModel).where(LessonModel.lesson_id.in_(set(lesson_ids.values())))
        existing = {lesson.lesson_id: lesson for lesson in (await db.execute(existing_stmt)).scalars()}

        created = updated = 0
        for key, spec in lessons.items():
            lesson_id = lesson_ids[key]
            class_id, subject_id, _date, topic_norm = key
            topic_id = topic_ids.get((class_id, subject_id, topic_norm))
            lesson = existing.get(lesson_id)
            if lesson is None:
                db.add(LessonModel(
                    lesson_id=lesson_id, class_id=class_id, subject_id=subject_id, teacher_id=teacher_id,
                    topic_id=topic_id, lesson_date=spec.lesson_date, lesson_number=spec.sequence + 1,
                    homework=spec.homework, academic_year=academic_year_for(spec.lesson_date),
                ))
                created += 1
                continue
            changed = False
            if topic_id is not None and lesson.topic_id != topic_id:
                lesson.topic_id = topic_id
                changed = True
            if spec.homework is not None and lesson.homework != spec.homework:
                lesson.homework = spec.homework
                changed = True
            updated += 1 if changed else 0
        await db.flush()
        return lesson_ids, created, updated

    @staticmethod
    async def _upsert_grades(db: AsyncSession, result, lesson_ids: dict):
        if not result.grades: return 0, 0, set()
        
        existing_stmt = select(GradeModel).where(GradeModel.lesson_id.in_({lesson_ids[key] for key, _ in result.grades}))
        existing = {(grade.lesson_id, grade.student_id): grade for grade in (await db.execute(existing_stmt)).scalars()}

        created = updated = 0
        new_grades = []
        affected_streaks = set()
        
        for (lesson_key, student_id), (value, work_type, homework_status) in result.grades.items():
            lesson_id = lesson_ids[lesson_key]
            grade = existing.get((lesson_id, student_id))
            
            if value is not None:
                if grade is None:
                    new_grades.append(GradeModel(
                        lesson_id=lesson_id, student_id=student_id, value=value, work_type=work_type,
                        academic_year=academic_year_for(result.lessons[lesson_key].lesson_date), source=GradeSource.MANUAL,
                    ))
                    created += 1
                elif grade.value != value or grade.work_type != work_type:
                    grade.value = value
                    grade.work_type = work_type
                    updated += 1

            if work_type == "homework":
                affected_streaks.add((
                    student_id, 
                    result.lessons[lesson_key].subject_id, 
                    academic_year_for(result.lessons[lesson_key].lesson_date)
                ))

            # B1: Логика долгов
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            debt_q = select(DebtModel).where(
                DebtModel.student_id == student_id,
                DebtModel.lesson_id == lesson_id,
                DebtModel.resolved.is_(False)
            )
            active_debt = (await db.execute(debt_q)).scalar_one_or_none()

            if value is not None and value >= 3:
                if active_debt:
                    active_debt.resolved = True
                    active_debt.resolved_at = now_utc
            elif (value is not None and value <= 2) or (homework_status and homework_status in ("missing", "не сделано", "not done")):
                if not active_debt:
                    debt_type = DebtType.GRADE2 if (value is not None and value <= 2) else DebtType.HOMEWORK
                    db.add(DebtModel(
                        student_id=student_id,
                        lesson_id=lesson_id,
                        type=debt_type,
                        resolved=False,
                        academic_year=academic_year_for(result.lessons[lesson_key].lesson_date),
                    ))

        if new_grades:
            await _sync_sequence(db, GradeModel, "grade_id")
            db.add_all(new_grades)
        return created, updated, affected_streaks

    # B2: Пересчёт стриков
    @staticmethod
    async def _update_streaks(db: AsyncSession, affected: set[tuple[int, int, int]]):
        for student_id, subject_id, year in affected:
            q = (
                select(GradeModel.value, LessonModel.lesson_date)
                .join(LessonModel, GradeModel.lesson_id == LessonModel.lesson_id)
                .where(
                    GradeModel.student_id == student_id,
                    LessonModel.subject_id == subject_id,
                    GradeModel.work_type == "homework",
                    GradeModel.academic_year == year,
                )
                .order_by(LessonModel.lesson_date.desc(), LessonModel.lesson_number.desc())
            )
            rows = (await db.execute(q)).all()
            
            streak = 0
            for val, _ in rows:
                if val >= 3:
                    streak += 1
                else:
                    break
                    
            last_done = next((d for v, d in rows if v >= 3), None)

            streak_q = select(StreakModel).where(
                StreakModel.student_id == student_id,
                StreakModel.subject_id == subject_id,
                StreakModel.academic_year == year,
            )
            streak_obj = (await db.execute(streak_q)).scalar_one_or_none()
            
            if streak_obj:
                streak_obj.current_streak = streak
                streak_obj.last_homework_done = last_done
            else:
                db.add(StreakModel(
                    student_id=student_id,
                    subject_id=subject_id,
                    current_streak=streak,
                    last_homework_done=last_done,
                    academic_year=year,
                ))