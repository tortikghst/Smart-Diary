from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from uuid import UUID


class ClassStudentSchema(BaseModel):
    """Схема студента для рассадки и журнала (Страница 6 Контракта)"""

    student_id: int
    full_name: str

    class Config:
        from_attributes = True


class JournalGradeResponse(BaseModel):
    student_id: int
    value: int

    class Config:
        from_attributes = True


class JournalLessonResponse(BaseModel):
    lesson_id: UUID
    lesson_date: date
    lesson_number: Optional[int] = None
    topic_title: Optional[str] = None
    homework: Optional[str] = None
    grades: List[JournalGradeResponse] = []

    class Config:
        from_attributes = True


class FullJournalResponse(BaseModel):
    """Схема финального ответа для сетки успеваемости (Страница 6 Контракта)"""

    students: List[ClassStudentSchema]
    lessons: List[JournalLessonResponse]
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True
