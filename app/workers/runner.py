from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_TASKS: dict[str, Callable[..., Any]] = {}
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hrms-worker")


def register_task(name: str, func: Callable[..., Any]) -> None:
    _TASKS[name] = func


def _get_rq_queue():
    settings = get_settings()
    if not settings.worker_use_rq or not settings.redis_url:
        return None
    try:
        from redis import Redis
        from rq import Queue

        conn = Redis.from_url(settings.redis_url)
        return Queue(settings.worker_queue_name, connection=conn)
    except Exception:
        logger.warning("RQ unavailable; falling back to thread pool", exc_info=True)
        return None


def enqueue(task_name: str, *args: Any, **kwargs: Any) -> str:
    """Enqueue a background task. Uses RQ when Redis is configured, else thread pool."""
    func = _TASKS.get(task_name)
    if not func:
        raise ValueError(f"Unknown task: {task_name}")

    queue = _get_rq_queue()
    if queue is not None:
        job = queue.enqueue(func, *args, **kwargs)
        logger.info("Enqueued RQ job %s id=%s", task_name, job.id)
        return job.id

    _executor.submit(func, *args, **kwargs)
    logger.info("Submitted thread-pool job %s", task_name)
    return "thread-pool"


def run_sync(task_name: str, *args: Any, **kwargs: Any) -> Any:
    func = _TASKS.get(task_name)
    if not func:
        raise ValueError(f"Unknown task: {task_name}")
    return func(*args, **kwargs)
