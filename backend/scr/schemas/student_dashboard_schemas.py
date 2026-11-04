from pydantic import BaseModel
from typing import List, Optional


class DashboardSubjectSchema(BaseModel):
    subject_id: int
    name: str


class DashboardStreakSchema(BaseModel):
    current_streak: int


class DashboardAvailableTestSchema(BaseModel):
    test_id: int
    topic_title: str
    subject_name: str
    attempts_used: int
    attempts_left: int
    best_percent: Optional[int] = None


class StudentDashboardResponse(BaseModel):
    subjects: List[DashboardSubjectSchema]
    streak: DashboardStreakSchema
    debts_count: int
    available_tests: List[DashboardAvailableTestSchema]

    class Config:
        from_attributes = True
