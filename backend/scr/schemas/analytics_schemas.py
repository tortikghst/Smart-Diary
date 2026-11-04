from pydantic import BaseModel
from datetime import date
from typing import List, Optional


class AnalyticsPeriodSchema(BaseModel):
    date_from: date
    date_to: date


class AnalyticsBigNumbersSchema(BaseModel):
    # B4: None означает «нет оценок», фронт рисует прочерк
    avg_score: Optional[float] = None
    active_debts: int


class AnalyticsGradeDistributionSchema(BaseModel):
    grade_5: int
    grade_4: int
    grade_3: int
    grade_2: int


class AnalyticsTopicAvgSchema(BaseModel):
    topic_id: int
    topic_title: str
    avg_score: float
    # B3: метрики для рекомендации с цифрами
    grades_count: int = 0
    mastery_percent: int = 0
    students_with_gaps: int = 0


class ClassAnalyticsResponse(BaseModel):
    class_id: int
    period: AnalyticsPeriodSchema
    big_numbers: AnalyticsBigNumbersSchema
    grade_distribution: AnalyticsGradeDistributionSchema
    topics_avg: List[AnalyticsTopicAvgSchema]
    weakest_topic: Optional[AnalyticsTopicAvgSchema] = None
    ai_recommendation: Optional[str] = None

    class Config:
        from_attributes = True