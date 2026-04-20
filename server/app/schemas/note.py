from pydantic import BaseModel, ConfigDict


class NoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    title: str | None = None


class NoteReplayActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = None


class NoteResponse(BaseModel):
    id: str
    title: str
    summary: str | None
    canonical_text: str | None
    category: str | None
    status: str
    asset_id: str | None
    primary_time: str | None


class NoteCreateResponse(BaseModel):
    note_id: str
    job_id: str
