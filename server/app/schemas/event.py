from pydantic import BaseModel


class EventResponse(BaseModel):
    id: str
    title: str
    summary: str | None
    event_type: str | None
    start_time: str | None
    end_time: str | None
    time_precision: str
    time_text: str | None


class EventDetailResponse(EventResponse):
    participants: list[dict] = []
