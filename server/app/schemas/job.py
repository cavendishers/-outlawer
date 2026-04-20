from typing import Any

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    target_type: str
    target_id: str
    error_message: str | None = None
    retry_count: int = 0
    created_at: str | None = None
    finished_at: str | None = None


class JobDetailResponse(JobResponse):
    payload_json: dict[str, Any] = Field(default_factory=dict)
    result_json: dict[str, Any] = Field(default_factory=dict)


class JobRetryResponse(BaseModel):
    job_id: str
    status: str
