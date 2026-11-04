from pydantic import BaseModel
from typing import List


class RatingItemSchema(BaseModel):
    place: int
    class_id: int
    class_name: str
    avg_score: float

    class Config:
        from_attributes = True


class StudentRatingResponse(BaseModel):
    type: str
    items: List[RatingItemSchema]
    my_class_id: int

    class Config:
        from_attributes = True
