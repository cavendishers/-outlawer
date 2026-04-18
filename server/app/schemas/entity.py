from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: str
    entity_type: str
    canonical_name: str
    display_name: str
    description: str | None
    aliases: list[str]


class EntityDetailResponse(EntityResponse):
    related_events: list[dict] = []
