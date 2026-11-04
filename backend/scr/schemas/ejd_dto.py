from uuid import UUID
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class LessonDTO(BaseModel):
    lesson_id: UUID
    class_id: int
    subject_id: int
    teacher_id: int
    topic: str
    date: date
    sequence: int = 0
    homework: str | None = None
    source: Literal["excel", "api"]


class GradeDTO(BaseModel):
    student_id: int
    lesson_id: UUID
    value: int = Field(ge=1, le=5)
    source: Literal["regular", "control", "vpr"]


class AttendanceDTO(BaseModel):
    student_id: int
    lesson_id: UUID
    present: bool


class HomeworkStatusDTO(BaseModel):
    student_id: int
    lesson_id: UUID
    status: Literal["done", "missing", "not_assigned"]
    source: Literal["excel", "api"]


class StudentDTO(BaseModel):
    student_id: int
    full_name: str
    class_id: int
