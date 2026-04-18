from pydantic import BaseModel


class StoryViewResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    title: str
    content: str
    style_type: str
