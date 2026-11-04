from pydantic import BaseModel


class TeacherClassResponse(BaseModel):
    class_id: int
    class_name: str

    class Config:
        from_attributes = True
