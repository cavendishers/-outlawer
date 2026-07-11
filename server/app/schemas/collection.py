from pydantic import BaseModel, ConfigDict, Field


class CollectionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    collection_type: str = "topic"


class CollectionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    collection_type: str | None = None
    status: str | None = None


class CollectionItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: str
    item_id: str
    sort_order: int | None = None
    curator_note: str | None = None


class CollectionItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort_order: int | None = None
    curator_note: str | None = None


class CollectionStoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    summary: str | None = None
    body: str | None = None
    style: str = "documentary"


class CollectionItemResponse(BaseModel):
    id: str
    item_type: str
    item_id: str
    label: str
    subtitle: str | None = None
    href: str
    sort_order: int
    curator_note: str | None = None
    created_at: str | None = None


class CollectionStoryResponse(BaseModel):
    title: str | None = None
    summary: str | None = None
    body: str | None = None
    style: str


class CollectionResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    collection_type: str
    status: str
    item_count: int = 0
    story: CollectionStoryResponse
    created_at: str | None = None
    updated_at: str | None = None


class CollectionDetailResponse(CollectionResponse):
    items: list[CollectionItemResponse] = Field(default_factory=list)


class CollectionDeletedResponse(BaseModel):
    id: str
    status: str


class CollectionItemDeletedResponse(BaseModel):
    id: str
    status: str


class CollectionTimelineItemResponse(BaseModel):
    event_id: str
    title: str
    summary: str | None = None
    display_time: str | None = None
    sort_time: str | None = None
    location_text: str | None = None
    curator_note: str | None = None
    href: str


class CollectionTimelineResponse(BaseModel):
    collection_id: str
    items: list[CollectionTimelineItemResponse] = Field(default_factory=list)


class CollectionExportResponse(BaseModel):
    format: str
    filename: str
    mime_type: str
    content: str
