from pydantic import BaseModel, Field
from typing import List, Tuple, Optional


class Position(BaseModel):
    row: int
    col: int


class Seat(Position):
    student_id: int
    markers: List[str] = []


class SeatingLayout(BaseModel):
    grid: dict = Field(default={"rows": 5, "cols": 6})
    seats: List[Seat]
    teacher: Position
    conflicts: List[Tuple[int, int]] = []
    excluded_student_ids: List[int] = []


class SeatingUpdateRequest(BaseModel):
    """Схема запроса от фронтенда (БЕЗ teacher_position)"""

    layout_json: SeatingLayout


class SeatingResponse(BaseModel):
    """Сchema ответа фронтенду (с вычисленной позицией)"""

    class_id: int
    layout_json: SeatingLayout
    teacher_position: str
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True
