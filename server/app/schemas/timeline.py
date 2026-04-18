from pydantic import BaseModel


class TimelineItemResponse(BaseModel):
    id: str
    event_id: str | None
    note_id: str | None
    title: str
    summary: str | None
    display_time: str | None
    sort_time: str | None
    time_precision: str
