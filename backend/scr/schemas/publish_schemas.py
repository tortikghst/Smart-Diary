from uuid import UUID
from pydantic import BaseModel


class PublishTestRequest(BaseModel):
    """
    УПРОЩЕННЫЙ КОНТРАКТ: Вырезаны лишние поля max_attempts и deadline.
    Принимает строго то, что учитель нажимает в один клик по Miro.
    """

    test_id: int
    lesson_id: UUID  # Идентификатор урока в формате UUID


class PublishTestResponse(BaseModel):
    """Схема ответа после успешной публикации"""

    message: str
    test_id: int
    lesson_id: UUID
    homework_updated_text: str
