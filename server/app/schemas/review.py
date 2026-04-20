from typing import Literal

from pydantic import BaseModel, ConfigDict


class MergeCandidateRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = "rejected_by_user"
    note: str | None = None


class MergeCandidateAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: Literal["merge", "alias_only"] = "merge"
    survivor_id: str | None = None
    note: str | None = None


class ConfirmEntityAliasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str
    note: str | None = None
