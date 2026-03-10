import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "market_dashboard.settings")

app = Celery("market_dashboard")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Uses CELERY_TIMEZONE from Django settings
app.conf.beat_schedule = {
    "check-alerts-every-10-minutes": {
        "task": "stocks.tasks.check_alerts",
        "schedule": crontab(minute="*/5"),
    },
    "weekly-digest-monday-6am-est": {
        "task": "stocks.tasks.send_weekly_digest",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),
    },
}
