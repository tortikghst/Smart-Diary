from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

class DashboardTestSchema(BaseModel):
    test_id: int
    topic_id: int
    topic_title: str
    class_id: int
    status: str
    lesson_id: Optional[UUID] = None  # <--- ДОБАВИЛИ ЭТО ПОЛЕ

class DashboardClassSchema(BaseModel):
    class_id: int
    class_name: str
    # B4: None = нет оценок, фронт рисует прочерк
    avg_score: Optional[float] = None
    debts_count: int
    is_problem: bool


class DashboardMetricsSchema(BaseModel):
    total_open_debts: int
    active_academic_year: int


class DashboardTomorrowTopicSchema(BaseModel):
    class_name: str
    topic: str


class DashboardTestSchema(BaseModel):
    test_id: int
    topic_id: int
    topic_title: str
    class_id: int
    status: str


class TeacherDashboardResponse(BaseModel):
    classes: List[DashboardClassSchema]
    problem_class_id: Optional[int] = None
    metrics: DashboardMetricsSchema
    tomorrow_topics: Optional[List[DashboardTomorrowTopicSchema]] = None
    tests: List[DashboardTestSchema]

    class Config:
        from_attributes = True