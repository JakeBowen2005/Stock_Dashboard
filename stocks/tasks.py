from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from . import finnhub_client
from .push_utils import send_push_to_user

User = get_user_model()

ALERT_COOLDOWN_HOURS = 24
RESET_BUFFER_PCT = 0.5  # percentage points / relative buffer used to re-arm alerts


def _recommendation_snippet(rec):
    if not rec:
        return ""
    period = rec.get("period", "n/a")
    strong_buy = rec.get("strongBuy", 0)
    buy = rec.get("buy", 0)
    hold = rec.get("hold", 0)
    sell = rec.get("sell", 0)
    strong_sell = rec.get("strongSell", 0)
    return f" | Anaylyst Recommendations from {period}: Strong buys {strong_buy} | Buys {buy} | Hold {hold} | Sell | {sell} Strong Sell {strong_sell} |"


def _triggered(alert, current, threshold, pct_change):
    if alert.alert_type == "price":
        if alert.direction == "above":
            return current >= threshold
        return current <= threshold

    if pct_change is None:
        return False

    if alert.direction == "above":
        return pct_change >= threshold
    return pct_change <= -abs(threshold)


def _rearm_condition(alert, current, threshold, pct_change):
    if alert.alert_type == "price":
        if alert.direction == "above":
            reset_line = threshold * (1 - (RESET_BUFFER_PCT / 100.0))
            return current <= reset_line
        reset_line = threshold * (1 + (RESET_BUFFER_PCT / 100.0))
        return current >= reset_line

    if pct_change is None:
        return False

    if alert.direction == "above":
        return pct_change <= (threshold - RESET_BUFFER_PCT)
    return pct_change >= (-abs(threshold) + RESET_BUFFER_PCT)


@shared_task
def check_alerts():
    from .models import StockAlert

    active = StockAlert.objects.select_related("user")
    if not active.exists():
        return

    now = timezone.now()

    # Group by ticker to minimise API calls
    by_ticker = {}
    for alert in active:
        by_ticker.setdefault(alert.ticker, []).append(alert)

    for ticker, alerts in by_ticker.items():
        quote = finnhub_client.get_quote(ticker)
        current = quote.get("c")
        if not current:
            continue

        rec = finnhub_client.get_recommendations(ticker)
        rec_text = _recommendation_snippet(rec)

        for alert in alerts:
            threshold = float(alert.threshold)
            pct_change = None

            if alert.alert_type == "pct" and alert.baseline_price:
                baseline = float(alert.baseline_price)
                if baseline != 0:
                    pct_change = (current - baseline) / baseline * 100

            condition_met = _triggered(alert, current, threshold, pct_change)

            # Alert is currently latched; wait for reset condition before allowing another alert.
            if not alert.rearm_ready:
                if _rearm_condition(alert, current, threshold, pct_change):
                    alert.rearm_ready = True
                    alert.save(update_fields=["rearm_ready"])
                continue

            # Cooldown guard (max one notification per day per alert).
            if alert.last_notified_at:
                hours_since_last = (now - alert.last_notified_at).total_seconds() / 3600
                if hours_since_last < ALERT_COOLDOWN_HOURS:
                    continue

            if not condition_met:
                continue

            direction_word = "above" if alert.direction == "above" else "below"
            if alert.alert_type == "price":
                msg = f"{ticker} is now ${current:.2f} ({direction_word} ${threshold:.2f}){rec_text}"
            else:
                if pct_change is None:
                    continue
                msg = f"{ticker} moved {pct_change:+.2f}% ({direction_word} {threshold:.1f}% target){rec_text}"

            send_push_to_user(
                alert.user,
                title=f"Price Alert: {ticker}",
                body=msg,
                url=f"/stock/{ticker}/",
            )

            alert.triggered = True
            alert.rearm_ready = False
            alert.last_notified_at = now
            alert.save(update_fields=["triggered", "rearm_ready", "last_notified_at"])


@shared_task
def send_weekly_digest():
    from .models import WatchList

    users_with_subs = User.objects.filter(push_subscriptions__isnull=False).distinct()

    for user in users_with_subs:
        try:
            watchlist = WatchList.objects.get(user=user)
        except WatchList.DoesNotExist:
            continue

        tickers = list(watchlist.items.values_list("ticker", flat=True))
        if not tickers:
            continue

        lines = []
        for ticker in tickers:
            quote = finnhub_client.get_quote(ticker)
            c = quote.get("c")
            pc = quote.get("pc")
            if c and pc and pc != 0:
                chg = (c - pc) / pc * 100
                arrow = "▲" if chg >= 0 else "▼"
                lines.append(f"{ticker}: ${c:.2f} {arrow}{abs(chg):.1f}%")
            elif c:
                lines.append(f"{ticker}: ${c:.2f}")

        if not lines:
            continue

        body = "  |  ".join(lines)
        send_push_to_user(
            user,
            title="Weekly Market Digest",
            body=body,
            url="/analyze/",
        )
