import os
import time

import requests

_BASE = "https://finnhub.io/api/v1"
_TIMEOUT_SECONDS = 6
_RETRY_DELAYS_SECONDS = (0.5, 1.0, 2.0)


def _key():
    return os.getenv("FINNHUB_API_KEY", "")


def _request_json(path, params):
    token = _key()
    if not token:
        return None

    full_params = dict(params)
    full_params["token"] = token

    last_status = None
    for attempt in range(len(_RETRY_DELAYS_SECONDS) + 1):
        try:
            response = requests.get(
                f"{_BASE}{path}",
                params=full_params,
                timeout=_TIMEOUT_SECONDS,
            )
            last_status = response.status_code

            if response.status_code == 200:
                return response.json()

            # Retry temporary server and rate-limit failures.
            if response.status_code not in (429, 500, 502, 503, 504):
                return None
        except requests.RequestException:
            pass

        if attempt < len(_RETRY_DELAYS_SECONDS):
            time.sleep(_RETRY_DELAYS_SECONDS[attempt])

    if last_status == 429:
        print("[finnhub] rate limited after retries.")
    return None


def get_quote(symbol):
    """Returns dict with c (current), pc (prev close), h, l, o or empty dict on error."""
    data = _request_json("/quote", {"symbol": symbol})
    if not data:
        return {}
    return data if data.get("c") else {}


def get_recommendations(symbol):
    """Returns the most recent analyst recommendation period or None."""
    data = _request_json("/stock/recommendation", {"symbol": symbol})
    if not data:
        return None
    return data[0] if isinstance(data, list) and data else None
