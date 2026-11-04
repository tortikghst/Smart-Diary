from pydantic import BaseModel
from datetime import date
from typing import List, Optional


class GradeSubjectSchema(BaseModel):
    subject_id: int
    name: str


class DetailedStudentGradeSchema(BaseModel):
    grade_id: int
    value: int
    lesson_date: date
    topic_title: Optional[str] = None       # ← терпит None
    work_type: Optional[str] = "regular"    # ← терпит None


class StudentSubjectGradesResponse(BaseModel):
    subject: GradeSubjectSchema
    avg_score: Optional[float] = None
    homework_percent: int
    grades: List[DetailedStudentGradeSchema]

    class Config:
        from_attributes = True