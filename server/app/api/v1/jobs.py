from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.serializers import serialize_job
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.models.ai_job import AIJob
from app.services.job_dispatcher import dispatch_job

router = APIRouter()


@router.get("")
def list_jobs(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size, max_page_size=50)
    query = select(AIJob).where(AIJob.user_id == user.id).order_by(AIJob.created_at.desc())
    jobs, total = paginate_query(db, query, params)
    return paginated(
        items=[serialize_job(job) for job in jobs],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{job_id}")
def get_job(job_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    job = db.get(AIJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return ok(serialize_job(job, include_result=True))


@router.post("/{job_id}/retry")
def retry_job(job_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    job = db.get(AIJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job.status = "pending"
    job.retry_count += 1
    job.error_message = None
    db.add(job)
    db.commit()
    dispatch_job(job)
    return ok({"job_id": job.id, "status": job.status})
