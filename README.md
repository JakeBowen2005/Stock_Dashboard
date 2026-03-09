# Market Dashboard

A Django-based stock analysis web app built on top of a custom Python analytics engine.

## Features
- Add up to 8 ticker symbols and analyze them in a card-based dashboard
- Click any stock card to open a deep-analysis page
- Metrics include momentum, CAGR, total return, volatility, drawdown, moving averages, and valuation
- Session-based add/remove ticker flow for quick experimentation

## Tech Stack
- Python
- Django
- pandas
- yfinance

## Local Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy env template:
   ```bash
   cp .env.example .env
   ```
4. Run migrations and start server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

## Deploy on Render
1. Push this repo to GitHub.
2. In Render, create a **PostgreSQL** database.
3. Create a new **Web Service** from this repo.
4. Configure:
   - Build Command: `./build.sh`
   - Start Command: `gunicorn market_dashboard.wsgi:application`
5. Add environment variables in Render:
   - `SECRET_KEY` = strong random string
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = your Render hostname (for example `stock-dashboard.onrender.com`)
   - `CSRF_TRUSTED_ORIGINS` = full URL (for example `https://stock-dashboard.onrender.com`)
   - `DATABASE_URL` = use the Render Postgres connection string
   - `SECURE_SSL_REDIRECT` = `True`
6. Deploy and open the live URL.

## Notes
- Home page `GET /` intentionally clears ticker session state to start a fresh list.
- Static files are served with WhiteNoise in production.
