import datetime
import random
import uuid

from sqlalchemy import select, text, delete
from scr.database import create_session
from scr.model.model import (
    UserModel, UserRole, SchoolClassesModel, SubjectModel, ClassSubjectModel,
    StudyPlanModel, StudyPlanStatus, PlanTopicModel, LessonModel, GradeModel,
    GradeSource, DebtModel, DebtType, StreakModel, ClassRatingModel,
    ClassRatingEventType, StudentMarkerModel, StudentMarker,
    TestModel, TestQuestionModel, TestCreatedBy, QuestionType
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

# 8Б (ID 4) и 9А (ID 5) будут проблемными
PROBLEM_CLASSES = {4, 5}

MALE_NAMES = ["Александр", "Дмитрий", "Максим", "Иван", "Артём", "Михаил", "Даниил", "Кирилл"]
FEMALE_NAMES = ["Мария", "Анна", "Елена", "Ольга", "Дарья", "София", "Виктория", "Полина"]
LAST_NAMES = ["Смирнов", "Иванов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Волков"]
MALE_PATRONYMICS = ["Александрович", "Дмитриевич", "Сергеевич", "Иванович", "Максимович"]
FEMALE_PATRONYMICS = ["Александровна", "Дмитриевна", "Сергеевна", "Ивановна", "Максимовна"]

TOPICS_BY_SUBJECT = {
    1: ["Дроби", "Квадратные уравнения", "Проценты", "Геометрия"],
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
            # Очистка (все таблицы, включая тесты)
            await session.execute(text("TRUNCATE users, classes, subjects, class_subjects, study_plans, plan_topics, lessons, grades, debts, streaks, class_ratings, student_markers, tests, test_questions, test_attempts, test_answers RESTART IDENTITY CASCADE;"))

            print("🌱 [BIG-SEED] Генерация идеального демо для хакатона...")

            # 1. Предметы
            for sid, name in SUBJECTS_DATA:
                session.add(SubjectModel(subject_id=sid, name=name))

            # 2. Учителя
            for uid, name, _sid in TEACHERS_DATA:
                vk_id = 12345 if uid == 101 else None
                session.add(UserModel(user_id=uid, vk_id=vk_id, full_name=name, role=UserRole.TEACHER))

            # 3. Классы
            for cid, cname, parallel in CLASSES_DATA:
                session.add(SchoolClassesModel(class_id=cid, class_name=cname, parallel=parallel, academic_year=year))
            
            await session.flush()

            # 4. Ученики
            student_id = 1000
            students_by_class = {cid: [] for cid, _, _ in CLASSES_DATA}
            
            for cid, cname, _ in CLASSES_DATA:
                for _ in range(10):
                    is_male = random.choice([True, False])
                    lname = random.choice(LAST_NAMES) + ("а" if not is_male else "")
                    fname = random.choice(MALE_NAMES if is_male else FEMALE_NAMES)
                    pname = random.choice(MALE_PATRONYMICS if is_male else FEMALE_PATRONYMICS)
                    full_name = f"{lname} {fname} {pname}"
                    
                    # Мок-вход для стартового ученика
                    vk_id = 23456 if student_id == 1000 else None
                    session.add(UserModel(
                        user_id=student_id, vk_id=vk_id, full_name=full_name, 
                        role=UserRole.STUDENT, class_id=cid
                    ))
                    students_by_class[cid].append(student_id)
                    student_id += 1
            await session.flush()

            # 5. Нагрузка
            for cid, _, _ in CLASSES_DATA:
                for teacher_id, _, sid in TEACHERS_DATA:
                    session.add(ClassSubjectModel(class_id=cid, subject_id=sid, teacher_id=teacher_id))
            await session.flush()

            # 6. Планы и темы
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

            # 7. Уроки и оценки (по 4 урока на класс-предмет)
            grade_id = 5000
            debt_id = 4000
            demo_debts_created = 0

            for cid, _, _ in CLASSES_DATA:
                is_problem_class = cid in PROBLEM_CLASSES
                
                for teacher_id, _, sid in TEACHERS_DATA:
                    topics = TOPICS_BY_SUBJECT[sid]
                    # 4 урока: 25, 18, 11, 4 дня назад
                    for i, days_ago in enumerate([25, 18, 11, 4]):
                        date = today - datetime.timedelta(days=days_ago)
                        topic_title = topics[i]
                        lesson_uuid = uuid.uuid4()
                        
                        session.add(LessonModel(
                            lesson_id=lesson_uuid, class_id=cid, subject_id=sid, teacher_id=teacher_id,
                            topic_id=topics_map[(cid, sid, topic_title)], lesson_date=date,
                            lesson_number=i+1, homework=f"ДЗ: {topic_title}", academic_year=year
                        ))

                        for st_id in students_by_class[cid]:
                            # Логика выставления оценок
                            if st_id == 1000:
                                # Стартовый ученик — отличник (5, 5, 4, 5)
                                grade_val = random.choices([5, 4, 3], weights=[70, 25, 5])[0]
                            elif is_problem_class:
                                # В проблемных классах много двоек и троек
                                grade_val = random.choices([5, 4, 3, 2], weights=[5, 15, 40, 40])[0]
                            else:
                                # В обычных классах норм (СДЕЛАЛИ ДВОЙКИ ОЧЕНЬ РЕДКИМИ)
                                grade_val = random.choices([5, 4, 3, 2], weights=[50, 35, 13, 2])[0]

                            # Принудительно делаем "адекватные" долги для демо-ученика
                            if st_id == 1000 and demo_debts_created < 2:
                                if sid == 1 and i == 1: # Долг по математике
                                    grade_val = 2
                                    demo_debts_created += 1
                                elif sid == 2 and i == 0: # Долг по русскому
                                    grade_val = 2
                                    demo_debts_created += 1

                            session.add(GradeModel(
                                grade_id=grade_id, lesson_id=lesson_uuid, student_id=st_id,
                                value=grade_val, work_type="homework" if i % 2 == 0 else "regular",
                                academic_year=year, source=GradeSource.MANUAL
                            ))
                            grade_id += 1

                            # Создаем долг, если 2 (и это не физра/труд). Сделали шанс долга ниже.
                            if grade_val == 2 and sid not in [9, 10] and random.random() > 0.5:
                                session.add(DebtModel(
                                    debt_id=debt_id, student_id=st_id, lesson_id=lesson_uuid,
                                    type=DebtType.GRADE2, resolved=False, academic_year=year
                                ))
                                debt_id += 1

            # 8. Стрики (Огоньки)
            for cid, _, _ in CLASSES_DATA:
                for st_id in students_by_class[cid]:
                    for _, _, sid in TEACHERS_DATA:
                        if st_id == 1000:
                            # У стартового ученика по математике огонек 15 дней!
                            if sid == 1: current_streak = 15
                            elif sid == 2: current_streak = 5
                            else: current_streak = random.randint(0, 3)
                        else:
                            current_streak = random.randint(0, 10) if random.random() > 0.3 else 0
                            
                        if current_streak > 0:
                            session.add(StreakModel(student_id=st_id, subject_id=sid, current_streak=current_streak, academic_year=year))

            # 9. Маркеры (для рассадки)
            for cid, _, _ in CLASSES_DATA:
                for st_id in students_by_class[cid]:
                    if random.random() > 0.8:
                        session.add(StudentMarkerModel(student_id=st_id, class_id=cid, marker=StudentMarker.FRONT_ROW_PREFERENCE))
                    elif random.random() > 0.9:
                        session.add(StudentMarkerModel(student_id=st_id, class_id=cid, marker=StudentMarker.SEPARATION_REQUIRED))

            # 10. Рейтинг классов
            rating_id = 1
            for cid, _, _ in CLASSES_DATA:
                # Проблемные классы имеют низкий балл
                base_score = random.uniform(2.8, 3.4) if cid in PROBLEM_CLASSES else random.uniform(4.2, 4.8)
                
                for ev_type in [ClassRatingEventType.EXAM, ClassRatingEventType.VPR]:
                    session.add(ClassRatingModel(
                        class_rating_id=rating_id, class_id=cid, event_date=today, 
                        avg_score=round(base_score + random.uniform(-0.2, 0.2), 1), 
                        event_type=ev_type
                    ))
                    rating_id += 1

            # 11. Генерация тестов для учителя математики (ID 101, класс 7А)
            test_id = 500
            # Публикуем тест для 7А по теме "Дроби"
            test1 = TestModel(
                test_id=test_id, topic_id=topics_map[(1, 1, "Дроби")], 
                created_by=TestCreatedBy.AI, status="published", title="Проверочная работа: Дроби"
            )
            session.add(test1)
            session.add(TestQuestionModel(
                test_id=test_id, type=QuestionType.CHOICE, 
                question="Какая дробь больше: 1/2 или 2/3?", 
                options={"options": ["1/2", "2/3", "Они равны"]}, correct_option_index=1
            ))
            session.add(TestQuestionModel(
                test_id=test_id, type=QuestionType.NUMERIC, 
                question="Сколько будет 1/4 + 1/4?", numeric_answer=0.5
            ))
            
            # Второй тест по теме "Проценты"
            test_id += 1
            test2 = TestModel(
                test_id=test_id, topic_id=topics_map[(1, 1, "Проценты")], 
                created_by=TestCreatedBy.AI, status="published", title="Тест на проценты"
            )
            session.add(test2)
            session.add(TestQuestionModel(
                test_id=test_id, type=QuestionType.CHOICE, 
                question="Сколько составляет 10% от 500?", 
                options={"options": ["10", "50", "100"]}, correct_option_index=1
            ))

            print("🌱 [BIG-SEED] Генерация завершена! Данные идеальны для демо.")