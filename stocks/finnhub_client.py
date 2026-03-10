import os
import requests

_BASE = "https://finnhub.io/api/v1"


def _key():
    return os.getenv("FINNHUB_API_KEY", "")


def get_quote(symbol):
    """Returns dict with c (current), pc (prev close), h, l, o or empty dict on error."""
    try:
        r = requests.get(
            f"{_BASE}/quote",
            params={"symbol": symbol, "token": _key()},
            timeout=5,
        )
        data = r.json()
        return data if data.get("c") else {}
    except Exception:
        return {}


def get_recommendations(symbol):
    """Returns the most recent analyst recommendation period or None."""
    try:
        r = requests.get(
            f"{_BASE}/stock/recommendation",
            params={"symbol": symbol, "token": _key()},
            timeout=5,
        )
        data = r.json()
        return data[0] if data else None
    except Exception:
        return None
