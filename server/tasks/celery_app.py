from celery import Celery
from server.config import settings

celery_app = Celery(
    "event_intel",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["server.tasks.send_task", "server.tasks.embedding_task"],
)

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
