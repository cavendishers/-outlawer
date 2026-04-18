from app.models.ai_job import AIJob
from app.tasks.pipeline import process_note_task


JOB_TASKS = {
    "knowledge_pipeline": process_note_task,
}


def dispatch_job(job: AIJob) -> None:
    task = JOB_TASKS.get(job.job_type)
    if task is None:
        raise ValueError(f"Unsupported job type: {job.job_type}")
    task.delay(job.id)
