web: gunicorn market_dashboard.wsgi:application
worker: python -m celery -A market_dashboard worker -l info
beat: python -m celery -A market_dashboard beat -l info
