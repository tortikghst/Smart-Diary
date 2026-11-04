from datetime import date
from pydantic import BaseModel


class StudentGradeResponse(BaseModel):
    """Схема ответа с оценкой для ученика"""

    grade_id: int
    value: int
    subject_name: str
    lesson_date: date

    class Config:
        from_attributes = True
