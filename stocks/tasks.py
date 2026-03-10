from celery import shared_task
from django.contrib.auth import get_user_model

from . import finnhub_client
from .push_utils import send_push_to_user

User = get_user_model()


@shared_task
def check_alerts():
    from .models import StockAlert

    active = StockAlert.objects.filter(triggered=False).select_related("user")
    if not active.exists():
        return

    # Group by ticker to minimise API calls
    by_ticker = {}
    for alert in active:
        by_ticker.setdefault(alert.ticker, []).append(alert)

    for ticker, alerts in by_ticker.items():
        quote = finnhub_client.get_quote(ticker)
        current = quote.get("c")
        if not current:
            continue

        for alert in alerts:
            threshold = float(alert.threshold)
            fired = False

            if alert.alert_type == "price":
                if alert.direction == "above" and current >= threshold:
                    fired = True
                elif alert.direction == "below" and current <= threshold:
                    fired = True
            else:  # pct
                if alert.baseline_price:
                    baseline = float(alert.baseline_price)
                    pct_change = (current - baseline) / baseline * 100
                    if alert.direction == "above" and pct_change >= threshold:
                        fired = True
                    elif alert.direction == "below" and pct_change <= -abs(threshold):
                        fired = True

            if fired:
                direction_word = "above" if alert.direction == "above" else "below"
                if alert.alert_type == "price":
                    msg = f"{ticker} is now ${current:.2f} ({direction_word} ${threshold:.2f})"
                else:
                    msg = f"{ticker} has moved {direction_word} {threshold:.1f}% from your set price"

                send_push_to_user(
                    alert.user,
                    title=f"Price Alert: {ticker}",
                    body=msg,
                    url=f"/stock/{ticker}/",
                )
                alert.triggered = True
                alert.save(update_fields=["triggered"])


@shared_task
def send_weekly_digest():
    from .models import PushSubscription, WatchList

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
