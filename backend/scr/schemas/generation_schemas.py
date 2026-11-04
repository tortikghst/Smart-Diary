from pydantic import BaseModel
from typing import List, Optional

class GenerateTestRequest(BaseModel):
    """Схема запроса на генерацию от учителя"""

    topic_id: int
    subject_id: int
    class_id: int
    title: str = "Новый тест"
    question_count: int = 2
    question_type: Optional[str] = None


class GeneratedQuestionResponse(BaseModel):
    """Схема вопроса внутри сгенерированного теста"""

    question_id: int
    type: str
    question: str
    options: Optional[dict] = None
    correct_option_index: Optional[int] = None  
    numeric_answer: Optional[float] = None
    class Config:
        from_attributes = True


class GenerateTestResponse(BaseModel):
    """Схема финального ответа для панели учителя"""

    test_id: int
    topic_id: int
    title: str
    created_by: str
    status: str = "draft"
    questions: List[GeneratedQuestionResponse]

    class Config:
        from_attributes = True