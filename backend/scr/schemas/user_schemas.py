from pydantic import BaseModel
from typing import Optional


class UserSubjectSchema(BaseModel):
    subject_id: int
    name: str


class UserMeResponse(BaseModel):
    user_id: int
    full_name: str
    role: str
    class_id: Optional[int] = None
    subject: Optional[UserSubjectSchema] = None

    class Config:
        from_attributes = True
