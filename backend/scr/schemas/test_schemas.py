from pydantic import BaseModel
from typing import List, Optional


class QuestionOptionSchema(BaseModel):
    """Схема для вариантов ответов (для вопросов типа choice)"""
    options: List[str]


class TestQuestionResponse(BaseModel):
    """Схема вопроса для ученика (БЕЗ правильного ответа)"""
    question_id: int
    type: str
    question: str
    options: Optional[dict] = None
    image_url: Optional[str] = None # <--- ДОБАВЛЕНО

    class Config:
        from_attributes = True


class TestResponse(BaseModel):
    """Схема самого теста со списком вопросов (для ученика и учителя при просмотре)"""
    test_id: int
    topic_id: int
    created_by: str
    status: str = "draft"
    questions: List[TestQuestionResponse]

    class Config:
        from_attributes = True


class AnswerInput(BaseModel):
    question_id: int
    answer: str


class SubmitTestRequest(BaseModel):
    answers: List[AnswerInput]


class SubmitTestResponse(BaseModel):
    """Схема ответа при сдаче теста (C4)."""
    attempt_id: int
    score: int
    passed: bool


class AIFeedbackItem(BaseModel):
    question_id: int
    question: str
    your_answer: str
    correct_answer: str
    explanation: Optional[str] = None
    image_url: Optional[str] = None # <--- ДОБАВЛЕНО


class AIFeedbackResponse(BaseModel):
    attempt_id: int
    items: List[AIFeedbackItem]


class PrepTestResponse(TestResponse):
    """C2: ответ на тренировочный тест по долгу. is_prep=True, без правильных ответов."""
    is_prep: bool = True


class QuestionSaveItem(BaseModel):
    """Схема вопроса для сохранения из конструктора учителя."""
    type: str
    question: str
    options: Optional[List[str]] = None
    correct_indices: Optional[List[int]] = None
    numeric_answer: Optional[float] = None
    image_url: Optional[str] = None # <--- ДОБАВЛЕНО


class TestSaveRequest(BaseModel):
    """Схема запроса на сохранение отредактированного теста."""
    topic_id: int
    questions: List[QuestionSaveItem]
    title: str = "Новый тест"


class QuestionEditResponse(BaseModel):
    """Схема вопроса для редактирования (С ПРАВИЛЬНЫМИ ответами)."""
    question_id: int
    type: str
    title: str
    question: str
    options: Optional[dict] = None
    correct_indices: Optional[List[int]] = None
    numeric_answer: Optional[float] = None
    image_url: Optional[str] = None # <--- ДОБАВЛЕНО


class TestEditResponse(BaseModel):
    """Схема теста для редактирования."""
    test_id: int
    topic_id: int
    created_by: str
    status: str
    questions: List[QuestionEditResponse]