import pandas as pd
import requests
import yfinance as yf

# Shared session with a real browser User-Agent so Yahoo Finance doesn't
# block requests coming from cloud IPs (Render, Heroku, etc.)
_SESSION = None

def _get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
    return _SESSION


def get_ticker(ticker):
    return yf.Ticker(ticker, session=_get_session())

def is_valid_ticker(ticker):
    try:
        hist = yf.Ticker(ticker, session=_get_session()).history(period="5d")
        return not hist.empty
    except Exception:
        return False

def get_history(ticker, period):
    try:
        history = ticker.history(period=period, auto_adjust=False)
    except Exception:
        history = pd.DataFrame()

    if history is None or history.empty:
        try:
            symbol = getattr(ticker, "ticker", "")
            history = yf.download(
                symbol,
                period=period,
                auto_adjust=False,
                progress=False,
                threads=False,
                session=_get_session(),
            )
        except Exception:
            history = pd.DataFrame()

    return history if history is not None else pd.DataFrame()

def get_financials(ticker):
    try:
        return ticker.financials
    except Exception:
        return pd.DataFrame()

def get_actions(ticker):
    try:
        return ticker.actions
    except Exception:
        return pd.DataFrame()

def get_balance_sheet(ticker):
    try:
        return ticker.balance_sheet
    except Exception:
        return pd.DataFrame()
