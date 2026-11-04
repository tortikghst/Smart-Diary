from datetime import date
from uuid import UUID  # СИНХРОНИЗАЦИЯ ТИПОВ: импортируем UUID
from pydantic import BaseModel
from typing import Optional


class StudentDebtResponse(BaseModel):
    """
    Схема ответа со списком задолженностей для дашборда ученика.
    Синхронизирована по типам UUID с моделью СУБД и картами Miro.
    """

    debt_id: int
    lesson_id: (
        UUID  # ДОБАВЛЕНО: строго UUID для сквозного перехода к тесту по картам Miro
    )
    type: str
    resolved: bool
    lesson_date: date
    subject_name: str
    topic_title: str

    class Config:
        from_attributes = True
