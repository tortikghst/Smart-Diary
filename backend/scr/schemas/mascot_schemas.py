from pydantic import BaseModel


class MascotResponse(BaseModel):
    subject_id: int
    mascot_type: str
    current_streak: int
    message: str