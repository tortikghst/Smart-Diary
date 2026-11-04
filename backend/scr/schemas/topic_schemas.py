from pydantic import BaseModel


class TopicLookupSchema(BaseModel):
    topic_id: int
    topic_title: str

    class Config:
        from_attributes = True
