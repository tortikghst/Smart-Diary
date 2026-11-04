from pydantic import BaseModel
from typing import Optional
from datetime import date


class StudentStreakResponse(BaseModel):
    """Схема ответа со стриками по предметам для ученика"""

    subject_id: int
    subject_name: str
    current_streak: int
    last_homework_done: Optional[date] = None

    class Config:
        from_attributes = True  # Чтобы читать данные из связанных моделей ORM
