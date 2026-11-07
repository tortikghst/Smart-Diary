import datetime
import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    DECIMAL,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ======================== Enum =====================
class UserRole(str, PyEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class StudyPlanStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"


class TestCreatedBy(str, PyEnum):
    AI = "ai"
    MANUAL = "manual"


class QuestionType(str, PyEnum):
    CHOICE = "choice"
    NUMERIC = "numeric"
    MATCHING = "matching"


class GradeSource(str, PyEnum):
    VOICE = "voice"
    MANUAL = "manual"


class DebtType(str, PyEnum):
    GRADE2 = "grade2"
    HOMEWORK = "homework"


class StudentMarker(str, PyEnum):
    FRONT_ROW_PREFERENCE = "front_row_preference"
    ACOUSTIC_PREFERENCE = "acoustic_preference"
    SEPARATION_REQUIRED = "separation_requered"


class ClassRatingEventType(str, PyEnum):
    EXAM = "exam"
    VPR = "vpr"


class TestAttemptStatus(str, PyEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ============================ Таблицы =====================


class SchoolClassesModel(Base):
    __tablename__ = "classes"

    class_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Уходит на фронт. Внутренние FK — на class_id.
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False
    )
    class_name: Mapped[str] = mapped_column(String(15), nullable=False)
    parallel: Mapped[int | None] = mapped_column(Integer, nullable=True)
    academic_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list["UserModel"]] = relationship(
        back_populates="school_class",
        cascade="save-update, merge",
    )
    lessons: Mapped[list["LessonModel"]] = relationship(
        back_populates="school_class",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    class_subjects: Mapped[list["ClassSubjectModel"]] = relationship(
        back_populates="school_class",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    seating: Mapped[list["SeatingModel"]] = relationship(
        back_populates="school_class",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    student_markers: Mapped[list["StudentMarkerModel"]] = relationship(
        back_populates="school_class",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    class_ratings: Mapped[list["ClassRatingModel"]] = relationship(
        back_populates="school_class",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False
    )
    vk_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Источник истины по правам — только role. is_admin убран.
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=True),
        default=UserRole.STUDENT,
        nullable=False,
    )
    class_id: Mapped[int | None] = mapped_column(
        ForeignKey("classes.class_id", ondelete="SET NULL"), nullable=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    school_class: Mapped[SchoolClassesModel | None] = relationship(
        back_populates="users"
    )
    class_subjects: Mapped[list["ClassSubjectModel"]] = relationship(
        back_populates="teacher",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    study_plans: Mapped[list["StudyPlanModel"]] = relationship(
        back_populates="teacher",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    lessons: Mapped[list["LessonModel"]] = relationship(
        back_populates="teacher",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    grades: Mapped[list["GradeModel"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    test_attempts: Mapped[list["TestAttemptModel"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    debts: Mapped[list["DebtModel"]] = relationship(
        back_populates="student",
        foreign_keys="DebtModel.student_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    student_markers: Mapped[list["StudentMarkerModel"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    streaks: Mapped[list["StreakModel"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    homework_submissions: Mapped[list["HomeworkSubmissionModel"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SubjectModel(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    class_subjects: Mapped[list["ClassSubjectModel"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    study_plans: Mapped[list["StudyPlanModel"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    lessons: Mapped[list["LessonModel"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    streaks: Mapped[list["StreakModel"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ClassSubjectModel(Base):
    __tablename__ = "class_subjects"

    class_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        primary_key=True,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.subject_id", ondelete="CASCADE"),
        primary_key=True,
    )
    teacher_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    schedule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    school_class: Mapped[SchoolClassesModel] = relationship(
        back_populates="class_subjects"
    )
    subject: Mapped[SubjectModel] = relationship(back_populates="class_subjects")
    teacher: Mapped[UserModel] = relationship(back_populates="class_subjects")


class StudyPlanModel(Base):
    __tablename__ = "study_plans"

    plan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    class_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    file_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[StudyPlanStatus] = mapped_column(
        Enum(StudyPlanStatus, name="study_plan_status_enum", native_enum=True),
        default=StudyPlanStatus.DRAFT,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    teacher: Mapped[UserModel] = relationship(back_populates="study_plans")
    subject: Mapped[SubjectModel] = relationship(back_populates="study_plans")
    topics: Mapped[list["PlanTopicModel"]] = relationship(
        back_populates="study_plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PlanTopicModel(Base):
    __tablename__ = "plan_topics"

    topic_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("study_plans.plan_id", ondelete="CASCADE"),
        nullable=False,
    )
    order_num: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    hours: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    study_plan: Mapped[StudyPlanModel] = relationship(back_populates="topics")
    lessons: Mapped[list["LessonModel"]] = relationship(
        back_populates="topic",
        cascade="save-update, merge",
    )
    tests: Mapped[list["TestModel"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "uq_plan_topics_current_per_plan",
            "plan_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )


class LessonModel(Base):
    __tablename__ = "lessons"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )  # ИЗМЕНЕНО: тип UUID вместо BigInteger
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False
    )
    class_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("plan_topics.topic_id", ondelete="SET NULL"),
        nullable=True,
    )
    lesson_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    lesson_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    homework: Mapped[str | None] = mapped_column(Text, nullable=True)
    academic_year: Mapped[int] = mapped_column(
        SmallInteger, default=2026, nullable=False
    )  # ДОБАВЛЕНО по §4 ТЗ
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    school_class: Mapped[SchoolClassesModel] = relationship(back_populates="lessons")
    subject: Mapped[SubjectModel] = relationship(back_populates="lessons")
    teacher: Mapped[UserModel] = relationship(back_populates="lessons")
    topic: Mapped[PlanTopicModel | None] = relationship(back_populates="lessons")
    grades: Mapped[list["GradeModel"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    debts: Mapped[list["DebtModel"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    submissions: Mapped[list["HomeworkSubmissionModel"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GradeModel(Base):
    __tablename__ = "grades"

    grade_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.lesson_id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    academic_year: Mapped[int] = mapped_column(
        SmallInteger, default=2026, nullable=False
    )

    # ДОБАВЛЕНО ПО ТЗ СТР. 9 и 12: Хранение каноничного типа работы
    work_type: Mapped[str] = mapped_column(
        String(50), default="regular", nullable=False
    )

    source: Mapped[GradeSource] = mapped_column(
        Enum(GradeSource, name="grade_source_enum", native_enum=True),
        default=GradeSource.MANUAL,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student: Mapped[UserModel] = relationship(back_populates="grades")
    lesson: Mapped[LessonModel] = relationship(back_populates="grades")


class TestModel(Base):
    __tablename__ = "tests"

    test_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.lesson_id", ondelete="SET NULL"),
        nullable=True,
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("plan_topics.topic_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[TestCreatedBy] = mapped_column(
        Enum(TestCreatedBy, name="test_created_by_enum", native_enum=True),
        default=TestCreatedBy.MANUAL,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # ДОБАВЛЕНО для управления публикацией (§9.5)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    topic: Mapped[PlanTopicModel] = relationship(back_populates="tests")
    questions: Mapped[list["TestQuestionModel"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attempts: Mapped[list["TestAttemptModel"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    title: Mapped[str] = mapped_column(String(255), default="Новый тест", server_default="Новый тест")

class TestQuestionModel(Base):
    __tablename__ = "test_questions"

    question_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    test_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tests.test_id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type_enum", native_enum=True),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correct_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numeric_answer: Mapped[float | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    test: Mapped[TestModel] = relationship(back_populates="questions")
    answers: Mapped[list["TestAnswerModel"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TestAttemptModel(Base):
    __tablename__ = "test_attempts"

    attempt_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    test_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tests.test_id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    started_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    passed_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[TestAttemptStatus] = mapped_column(
        Enum(TestAttemptStatus, name="test_attempt_status_enum", native_enum=True),
        default=TestAttemptStatus.IN_PROGRESS,
        nullable=False,
    )

    test: Mapped[TestModel] = relationship(back_populates="attempts")
    student: Mapped[UserModel] = relationship(back_populates="test_attempts")
    answers: Mapped[list["TestAnswerModel"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TestAnswerModel(Base):
    __tablename__ = "test_answers"

    attempt_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("test_attempts.attempt_id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("test_questions.question_id", ondelete="CASCADE"),
        primary_key=True,
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attempt: Mapped[TestAttemptModel] = relationship(back_populates="answers")
    question: Mapped[TestQuestionModel] = relationship(back_populates="answers")


class SeatingModel(Base):
    __tablename__ = "seating"

    seating_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    class_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        nullable=False,
    )
    layout_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    teacher_position: Mapped[str] = mapped_column(String(255), nullable=False)
    # ИСПРАВЛЕНО: photo_filename вместо photo_url под жесткие требования дискового хранилища ТЗ v6.0
    photo_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    school_class: Mapped[SchoolClassesModel] = relationship(back_populates="seating")


class DebtModel(Base):
    __tablename__ = "debts"

    debt_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(
            as_uuid=True
        ),  # ИЗМЕНЕНО: строго UUID для связывания задолженности с уроком
        ForeignKey("lessons.lesson_id", ondelete="CASCADE"),
        nullable=False,
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    type: Mapped[DebtType] = mapped_column(
        Enum(DebtType, name="debt_type_enum", native_enum=True),
        nullable=False,
    )
    academic_year: Mapped[int] = mapped_column(
        SmallInteger, default=2026, nullable=False
    )  # ДОБАВЛЕНО по §4 ТЗ
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    resolved_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    student: Mapped[UserModel] = relationship(
        back_populates="debts", foreign_keys=[student_id]
    )
    lesson: Mapped[LessonModel] = relationship(back_populates="debts")


class StudentMarkerModel(Base):
    __tablename__ = "student_markers"

    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    class_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        primary_key=True,
    )
    marker: Mapped[StudentMarker] = mapped_column(
        Enum(StudentMarker, name="student_marker_enum", native_enum=True),
        nullable=False,
    )

    school_class: Mapped[SchoolClassesModel] = relationship(
        back_populates="student_markers"
    )
    student: Mapped[UserModel] = relationship(back_populates="student_markers")


class HomeworkSubmissionModel(Base):
    __tablename__ = "homework_submissions"

    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    # ИСПРАВЛЕНО: тип UUID вместо BigInteger для совместимости с LessonModel
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.lesson_id", ondelete="CASCADE"),
        primary_key=True,
    )
    submitted_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped[UserModel] = relationship(back_populates="homework_submissions")
    lesson: Mapped[LessonModel] = relationship(back_populates="submissions")


class StreakModel(Base):
    __tablename__ = "streaks"

    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.subject_id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_homework_done: Mapped[datetime.date | None] = mapped_column(
        Date, nullable=True
    )
    academic_year: Mapped[int] = mapped_column(
        SmallInteger, default=2026, nullable=False
    )  # ДОБАВЛЕНО по §4 ТЗ
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student: Mapped[UserModel] = relationship(back_populates="streaks")
    subject: Mapped[SubjectModel] = relationship(back_populates="streaks")


class ClassRatingModel(Base):
    __tablename__ = "class_ratings"

    class_rating_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("classes.class_id", ondelete="CASCADE"),
    )
    event_date: Mapped[datetime.date] = mapped_column(Date)
    avg_score: Mapped[float] = mapped_column(DECIMAL(4, 2), nullable=False)
    event_type: Mapped[ClassRatingEventType] = mapped_column(
        Enum(
            ClassRatingEventType,
            name="class_rating_event_type_enum",
            native_enum=True,
        ),
        nullable=False,
    )
    computed_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    school_class: Mapped[SchoolClassesModel] = relationship(
        back_populates="class_ratings"
    )


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    actor_external_id: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # max_user_id или Сферум-ID
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # marker.update, debt.resolve, test.publish, etc.
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # student, debt, test
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_audit_log_created", "created_at"),
        Index("idx_audit_log_actor", "actor_user_id", "created_at"),
    )


class TechnicalLogModel(Base):
    __tablename__ = "technical_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # auth.rate_limited, llm_schema_mismatch
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # info, warning, error
    context_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_technical_log_created", "created_at"),)


class SyncLogModel(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)  # lesson, grade
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ok, partial, failed, correction, out_of_order
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_sync_log_created", "created_at"),)
