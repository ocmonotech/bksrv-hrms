"""Background workers — RQ with Redis, thread-pool fallback, optional APScheduler."""

from app.workers import tasks
from app.workers.runner import enqueue, register_task, run_sync
from app.workers.scheduler import start_scheduler, stop_scheduler

register_task("send_announcement", tasks.send_announcement_task)
register_task("send_payslip_notification", tasks.send_payslip_notification_task)
register_task("biometric_sync", tasks.biometric_sync_task)

__all__ = ["enqueue", "run_sync", "register_task", "start_scheduler", "stop_scheduler"]
