from celery import Celery

from app.config import settings

celery_app = Celery(
    "accessibility_copilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Route tasks to specific queues
    task_routes={
        "app.tasks.normalize_task.*": {"queue": "default"},
        "app.tasks.check_task.*": {"queue": "default"},
        "app.tasks.output_task.*": {"queue": "default"},
        "app.tasks.remediate_task.*": {"queue": "ai_remediation"},
        "app.tasks.video_normalizer_task.*": {"queue": "transcription"},
    },
    # Soft time limits (seconds)
    task_soft_time_limit=600,
    task_time_limit=660,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(
    [
        "app.tasks.normalize_task",
        "app.tasks.check_task",
        "app.tasks.remediate_task",
        "app.tasks.output_task",
    ]
)
