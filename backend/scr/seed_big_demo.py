import datetime
import random
import uuid

from sqlalchemy import select, text, delete
from scr.database import create_session
from scr.model.model import (
    UserModel, UserRole, SchoolClassesModel, SubjectModel, ClassSubjectModel,
    StudyPlanModel, StudyPlanStatus, PlanTopicModel, LessonModel, GradeModel,
    GradeSource, DebtModel, DebtType, StreakModel, ClassRatingModel,
    ClassRatingEventType, StudentMarkerModel, StudentMarker
)

SUBJECTS_DATA = [
    (1, "Математика"), (2, "Русский язык"), (3, "Литература"),
    (4, "История"), (5, "География"), (6, "Физика"),
    (7, "Химия"), (8, "Информатика"), (9, "Физическая культура"),
    (10, "Труд"), (11, "Биология"), (12, "Английский язык")
]

TEACHERS_DATA = [
    (101, "Иванов Иван Иванович", 1), (102, "Петрова Анна Сергеевна", 2),
    (103, "Сидоров Петр Алексеевич", 3), (104, "Смирнова Ольга Дмитриевна", 4),
    (105, "Кузнецов Андрей Николаевич", 5), (106, "Попова Елена Викторовна", 6),
    (107, "Волков Максим Олегович", 7), (108, "Морозова Дарья Игоревна", 8),
    (109, "Новиков Артем Павлович", 9), (110, "Федорова Мария Андреевна", 10),
    (111, "Белов Виктор Сергеевич", 11), (112, "Тихонова Алиса Валерьевна", 12)
]

CLASSES_DATA = [
    (1, "7А", 7), (2, "7Б", 7), (3, "8А", 8),
    (4, "8Б", 8), (5, "9А", 9), (6, "9Б", 9)
]

STUDENT_FIRST_NAMES = ["Александр", "Мария", "Дмитрий", "Анна", "Максим", "Елена", "Иван", "Ольга", "Артём", "Дарья"]
STUDENT_LAST_NAMES = ["Смирнов", "Иванов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Волков"]

TOPICS_BY_SUBJECT = {
    1: ["Дроби", "Уравнения", "Проценты", "Геометрия"],
    2: ["Причастия", "Деепричастия", "Синтаксис", "Орфография"],
    3: ["Пушкин", "Толстой", "Серебряный век", "Поэзия"],
    4: ["Древняя Русь", "Петр I", "Война 1812", "XX век"],
    5: ["Материки", "Климат", "Страны", "Океаны"],
    6: ["Электричество", "Механика", "Оптика", "Термодинамика"],
    7: ["Кислоты", "Основания", "Органика", "Металлы"],
    8: ["Алгоритмы", "Программирование", "Сети", "Базы данных"],
    9: ["Баскетбол", "Легкая атлетика", "Гимнастика", "Футбол"],
    10: ["Деревообработка", "Металл", "Кулинария", "Шитье"],
    11: ["Клетка", "Ботаника", "Зоология", "Анатомия"],
    12: ["Present Simple", "Past Continuous", "Articles", "Irregular Verbs"]
}

async def seed_big_demo():
    random.seed(42)
    today = datetime.date.today()
    year = today.year if today.month >= 9 else today.year - 1

    async with create_session() as session:
        async with session.begin():
            # 1. Полная очистка перед сидом (если что-то осталось)
            await session.execute(text("TRUNCATE users, classes, subjects, class_subjects, study_plans, plan_topics, lessons, grades, debts, streaks, class_ratings, student_markers RESTART IDENTITY CASCADE;"))

            print("🌱 [BIG-SEED] Начинаем генерацию огромного демо...")

            # 2. Предметы
            for sid, name in SUBJECTS_DATA:
                session.add(SubjectModel(subject_id=sid, name=name))

            # 3. Учителя (сразу привязываем мок-вход 'teacher' к математику, ID 101)
            for uid, name, _sid in TEACHERS_DATA:
                vk_id = 12345 if uid == 101 else None
                session.add(UserModel(user_id=uid, vk_id=vk_id, full_name=name, role=UserRole.TEACHER))

            # 4. Классы
            for cid, cname, parallel in CLASSES_DATA:
                session.add(SchoolClassesModel(class_id=cid, class_name=cname, parallel=parallel, academic_year=year))
            
            await session.flush()

            # 5. Ученики (10 на класс)
            student_id = 1000
            students_by_class = {cid: [] for cid, _, _ in CLASSES_DATA}
            
            for cid, cname, _ in CLASSES_DATA:
                for _ in range(10):
                    fname = random.choice(STUDENT_FIRST_NAMES)
                    lname = random.choice(STUDENT_LAST_NAMES)
                    # Привязываем мок-вход 'student' к первому ученику 7А (ID 1000)
                    vk_id = 23456 if student_id == 1000 else None
                    session.add(UserModel(
                        user_id=student_id, vk_id=vk_id, full_name=f"{lname} {fname}", 
                        role=UserRole.STUDENT, class_id=cid
                    ))
                    students_by_class[cid].append(student_id)
                    student_id += 1
            await session.flush()

            # 6. Нагрузка (класс-предмет-учитель)
            for cid, _, _ in CLASSES_DATA:
                for teacher_id, _, sid in TEACHERS_DATA:
                    session.add(ClassSubjectModel(class_id=cid, subject_id=sid, teacher_id=teacher_id))
            await session.flush()

            # 7. Планы и темы
            plan_id = 2000
            topic_id = 3000
            topics_map = {} 
            
            for cid, _, _ in CLASSES_DATA:
                for teacher_id, _, sid in TEACHERS_DATA:
                    session.add(StudyPlanModel(plan_id=plan_id, class_id=cid, subject_id=sid, teacher_id=teacher_id, status=StudyPlanStatus.ACTIVE))
                    for title in TOPICS_BY_SUBJECT[sid]:
                        session.add(PlanTopicModel(topic_id=topic_id, plan_id=plan_id, order_num=1, title=title, hours=2, quarter=1))
                        topics_map[(cid, sid, title)] = topic_id
                        topic_id += 1
                    plan_id += 1
            await session.flush()

            # 8. Уроки и оценки (по 2 урока на класс-предмет)
            grade_id = 5000
            debt_id = 4000
            
            for cid, _, _ in CLASSES_DATA:
                for teacher_id, _, sid in TEACHERS_DATA:
                    topics = TOPICS_BY_SUBJECT[sid]
                    for i, days_ago in enumerate([10, 2]): # 2 урока: старый и свежий
                        date = today - datetime.timedelta(days=days_ago)
                        topic_title = topics[i % len(topics)]
                        lesson_uuid = uuid.uuid4()
                        
                        session.add(LessonModel(
                            lesson_id=lesson_uuid, class_id=cid, subject_id=sid, teacher_id=teacher_id,
                            topic_id=topics_map[(cid, sid, topic_title)], lesson_date=date,
                            lesson_number=i+1, homework=f"ДЗ по теме {topic_title}", academic_year=year
                        ))

                        for st_id in students_by_class[cid]:
                            grade_val = random.choices([5, 4, 3, 2], weights=[30, 40, 20, 10])[0]
                            session.add(GradeModel(
                                grade_id=grade_id, lesson_id=lesson_uuid, student_id=st_id,
                                value=grade_val, work_type="homework" if i == 0 else "regular",
                                academic_year=year, source=GradeSource.MANUAL
                            ))
                            grade_id += 1

                            if grade_val == 2:
                                session.add(DebtModel(
                                    debt_id=debt_id, student_id=st_id, lesson_id=lesson_uuid,
                                    type=DebtType.GRADE2, resolved=False, academic_year=year
                                ))
                                debt_id += 1

            # 9. Стрики
            for cid, _, _ in CLASSES_DATA:
                for st_id in students_by_class[cid]:
                    for _, _, sid in TEACHERS_DATA:
                        if random.random() > 0.3:
                            session.add(StreakModel(student_id=st_id, subject_id=sid, current_streak=random.randint(1, 10), academic_year=year))

            # 10. Маркеры
            for cid, _, _ in CLASSES_DATA:
                for st_id in students_by_class[cid]:
                    if random.random() > 0.8:
                        session.add(StudentMarkerModel(student_id=st_id, class_id=cid, marker=StudentMarker.FRONT_ROW_PREFERENCE))
                    elif random.random() > 0.9:
                        session.add(StudentMarkerModel(student_id=st_id, class_id=cid, marker=StudentMarker.SEPARATION_REQUIRED))

            # 11. Рейтинг
            rating_id = 1
            for cid, _, _ in CLASSES_DATA:
                for ev_type in [ClassRatingEventType.EXAM, ClassRatingEventType.VPR]:
                    session.add(ClassRatingModel(class_rating_id=rating_id, class_id=cid, event_date=today, avg_score=round(random.uniform(3.0, 5.0), 1), event_type=ev_type))
                    rating_id += 1

            print("🌱 [BIG-SEED] Генерация завершена! Мок-входы привязаны, данные готовы.")