from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    target_type: str
    target_id: str
    error_message: str | None = None
    result_json: dict = {}
