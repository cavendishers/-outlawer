from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphViewpointCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    scope: str = "overview"
    anchor_type: str | None = None
    anchor_id: str | None = None
    filters_json: dict[str, Any] = Field(default_factory=dict)
    layout_json: dict[str, Any] = Field(default_factory=dict)


class GraphViewpointUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None


class GraphViewpointResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    scope: str
    anchor_type: str | None = None
    anchor_id: str | None = None
    filters_json: dict[str, Any] = Field(default_factory=dict)
    layout_json: dict[str, Any] = Field(default_factory=dict)
    href: str
    created_at: str | None = None
    updated_at: str | None = None


class GraphViewpointDeleteResponse(BaseModel):
    id: str
    status: str
