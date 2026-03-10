web: gunicorn market_dashboard.wsgi:application
worker: celery -A market_dashboard worker -B -l info
