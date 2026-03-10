import json
from datetime import timedelta
from urllib.parse import quote_plus

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from stock_market_analyzer.Stock_class import Stock

from . import finnhub_client
from .forms import SignUpForm
from .models import PushSubscription, StockAlert, WatchList, WatchListItem
from .push_utils import send_push_to_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_signal_snapshot(stock):
    checks = [
        ("1M momentum", stock["one_month_return"] is not None and stock["one_month_return"] > 0),
        ("6M momentum", stock["six_month_return"] is not None and stock["six_month_return"] > 0),
        ("Above 50-day MA", stock["above_50ma"] is True),
        ("Above 200-day MA", stock["above_200ma"] is True),
        ("5Y CAGR > 8%", stock["cagr_5y"] is not None and stock["cagr_5y"] > 8),
        ("10Y CAGR > 8%", stock["cagr_10y"] is not None and stock["cagr_10y"] > 8),
        ("10Y return > 100%", stock["total_return_10y"] is not None and stock["total_return_10y"] > 100),
        ("Drawdown better than -40%", stock["max_drawdown"] is not None and stock["max_drawdown"] > -40),
    ]

    positive_count = sum(1 for _, passed in checks if passed)
    total_count = len(checks)

    if positive_count >= 7:
        label = "Strong"
        tone = "positive"
        message = "Most trend and long-term indicators are supportive."
    elif positive_count >= 4:
        label = "Mixed"
        tone = "neutral"
        message = "Some signals are strong, but there are clear tradeoffs."
    else:
        label = "Caution"
        tone = "negative"
        message = "More risk flags than strength signals right now."

    return {
        "positive_count": positive_count,
        "total_count": total_count,
        "label": label,
        "tone": tone,
        "message": message,
        "checks": checks,
    }


def _format_currency(value):
    if value is None:
        return "—"
    return f"${value:,.2f}"


def _format_percent(value, digits=2):
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def _percent_class(value):
    if value is None:
        return "pct-neu"
    if value > 0:
        return "pct-pos"
    if value < 0:
        return "pct-neg"
    return "pct-neu"


def _dashboard_signal(stock):
    if stock.get("above_200ma") and (stock.get("cagr_5y") or 0) > 8 and (stock.get("one_month_return") or 0) > 0:
        return "Strong", "sig-strong"
    if stock.get("above_50ma") or (stock.get("cagr_5y") or 0) > 0:
        return "Mixed", "sig-mixed"
    return "Caution", "sig-caution"


def _get_or_create_user_watchlist(user):
    watchlist, _ = WatchList.objects.get_or_create(user=user)
    return watchlist


def _get_user_tickers(user):
    watchlist = _get_or_create_user_watchlist(user)
    return watchlist, list(
        watchlist.items.values_list("ticker", flat=True).order_by("ticker")
    )


def _build_alert_status(alert, now):
    cooldown_until = None
    if alert.last_notified_at:
        cooldown_until = alert.last_notified_at + timedelta(hours=24)

    if cooldown_until and now < cooldown_until:
        detail = f"Cooldown until {timezone.localtime(cooldown_until).strftime('%b %d, %I:%M %p')}."
        return "Cooldown", detail

    if not alert.rearm_ready:
        return "Waiting Reset", "Waiting for price to move away from trigger level."

    if alert.last_notified_at:
        detail = f"Last notified {timezone.localtime(alert.last_notified_at).strftime('%b %d, %I:%M %p')}."
        return "Re-armed", detail

    return "Ready", "Alert has not fired yet."


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "stocks/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            _, tickers = _get_user_tickers(user)
            if tickers:
                return redirect("analyze")
            return redirect("home")
    else:
        form = AuthenticationForm()
    return render(request, "stocks/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("login")


# ---------------------------------------------------------------------------
# Core pages
# ---------------------------------------------------------------------------

@login_required
def home(request):
    watchlist, added_stocks = _get_user_tickers(request.user)
    notice = ""

    if request.method == "GET":
        return render(request, "stocks/home.html", {
            "added_stocks": added_stocks,
            "notice": notice,
        })

    action = request.POST.get("action", "add")
    ticker = request.POST.get("ticker", "").strip().upper()

    if action == "remove":
        if ticker in added_stocks:
            WatchListItem.objects.filter(watchlist=watchlist, ticker=ticker).delete()
            notice = f"Removed {ticker}."
    else:
        if not ticker:
            notice = "Enter a ticker symbol."
        elif ticker in added_stocks:
            notice = f"{ticker} is already in your watchlist."
        elif len(added_stocks) >= 8:
            notice = "You can add up to 8 stocks."
        else:
            from stock_market_analyzer.data_loader import is_valid_ticker
            if not is_valid_ticker(ticker):
                notice = f"{ticker} is not a recognized ticker symbol."
            else:
                WatchListItem.objects.get_or_create(watchlist=watchlist, ticker=ticker)
                notice = f"Added {ticker}."

    _, added_stocks = _get_user_tickers(request.user)
    return render(request, "stocks/home.html", {
        "added_stocks": added_stocks,
        "notice": notice,
    })


@login_required
def analyze(request):
    _, added_stocks = _get_user_tickers(request.user)
    stock_summaries = []
    failed_tickers = []
    for ticker in added_stocks:
        try:
            stock_summaries.append(Stock(ticker).summary_dict())
        except Exception as exc:
            print(f"[analyze] failed ticker {ticker}: {exc}")
            failed_tickers.append(ticker)

    rows = []
    for stock in stock_summaries:
        signal_label, signal_class = _dashboard_signal(stock)
        rows.append(
            {
                "name": stock.get("name", "—"),
                "company_name": stock.get("company_name") or "Data unavailable",
                "current_price_display": _format_currency(stock.get("current_price")),
                "one_week_display": _format_percent(stock.get("one_week_return")),
                "one_week_class": _percent_class(stock.get("one_week_return")),
                "one_month_display": _format_percent(stock.get("one_month_return")),
                "one_month_class": _percent_class(stock.get("one_month_return")),
                "six_month_display": _format_percent(stock.get("six_month_return")),
                "six_month_class": _percent_class(stock.get("six_month_return")),
                "cagr_5y_display": _format_percent(stock.get("cagr_5y")),
                "cagr_5y_class": _percent_class(stock.get("cagr_5y")),
                "volatility_display": _format_percent(stock.get("volatility"), digits=1),
                "signal_label": signal_label,
                "signal_class": signal_class,
            }
        )

    def _average(values):
        valid = [v for v in values if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)

    portfolio = {
        "stocks_loaded": len(rows),
        "avg_one_month": _average([s.get("one_month_return") for s in stock_summaries]),
        "avg_six_month": _average([s.get("six_month_return") for s in stock_summaries]),
        "avg_cagr_5y": _average([s.get("cagr_5y") for s in stock_summaries]),
        "above_200ma_count": sum(1 for s in stock_summaries if s.get("above_200ma") is True),
        "price_sum": sum((s.get("current_price") or 0) for s in stock_summaries),
    }

    stock_count = len(rows)
    if stock_count >= 7:
        table_min_width = 1280
    elif stock_count >= 4:
        table_min_width = 1160
    else:
        table_min_width = 1040

    return render(request, "stocks/dashboard.html", {
        "stocks": stock_summaries,
        "rows": rows,
        "portfolio": portfolio,
        "table_min_width": table_min_width,
        "failed_tickers": failed_tickers,
        "alert_tickers": added_stocks,
    })


@login_required
def stock_detail(request, ticker):
    _get_or_create_user_watchlist(request.user)
    ticker = ticker.upper().strip()

    try:
        stock = Stock(ticker).summary_dict()
    except Exception:
        return render(request, "stocks/stock_detail.html", {
            "ticker": ticker,
            "error": "Could not load data for this ticker.",
        })

    signal_snapshot = _build_signal_snapshot(stock)

    mc = stock.get("market_cap")
    if mc is None:
        market_cap_display = "N/A"
    elif mc >= 1_000_000_000_000:
        market_cap_display = f"${mc / 1_000_000_000_000:.2f}T"
    elif mc >= 1_000_000_000:
        market_cap_display = f"${mc / 1_000_000_000:.2f}B"
    elif mc >= 1_000_000:
        market_cap_display = f"${mc / 1_000_000:.2f}M"
    else:
        market_cap_display = f"${mc:,.0f}"

    employees = stock.get("employees")
    employees_display = f"{employees:,}" if employees else "N/A"

    short_term_chart = {
        "labels": ["1W", "1M", "3M", "6M"],
        "values": [
            stock.get("one_week_return"),
            stock.get("one_month_return"),
            stock.get("three_month_return"),
            stock.get("six_month_return"),
        ],
    }
    long_term_chart = {
        "labels": ["5Y CAGR", "10Y CAGR", "10Y Total Return"],
        "values": [
            stock.get("cagr_5y"),
            stock.get("cagr_10y"),
            stock.get("total_return_10y"),
        ],
    }
    risk_chart = {
        "labels": ["Volatility", "Max Drawdown", "% from 52W High"],
        "values": [
            stock.get("volatility"),
            stock.get("max_drawdown"),
            stock.get("percent_from_high"),
        ],
    }

    recommendations = finnhub_client.get_recommendations(ticker)

    return render(request, "stocks/stock_detail.html", {
        "stock": stock,
        "signal": signal_snapshot,
        "market_cap_display": market_cap_display,
        "employees_display": employees_display,
        "short_term_chart": short_term_chart,
        "long_term_chart": long_term_chart,
        "risk_chart": risk_chart,
        "recommendations": recommendations,
        "vapid_public_key": settings.VAPID_PUBLIC_KEY,
        "finnhub_api_key": settings.FINNHUB_API_KEY,
    })


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@login_required
def alerts_view(request):
    _, user_tickers = _get_user_tickers(request.user)
    prefill_ticker = request.GET.get("ticker", "").upper()
    notification_notice = request.GET.get("notice", "")
    if not prefill_ticker and user_tickers:
        prefill_ticker = user_tickers[0]

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            alert_id = request.POST.get("alert_id")
            StockAlert.objects.filter(pk=alert_id, user=request.user).delete()
            return redirect("alerts")

        if action == "test_push":
            result = send_push_to_user(
                request.user,
                title="Test Alert: Market Dashboard",
                body="Push delivery is working. You can receive notifications.",
                url="/alerts/",
            )
            notice = (
                f"Test push attempted. Sent: {result['sent']}, "
                f"failed-kept: {result['kept_failed']}, removed-invalid: {result['deleted']}."
            )
            return redirect(f"{reverse('alerts')}?notice={quote_plus(notice)}")

        ticker = request.POST.get("ticker", "").strip().upper()
        alert_type = request.POST.get("alert_type")
        direction = request.POST.get("direction")
        threshold_raw = request.POST.get("threshold", "")
        try:
            threshold = float(threshold_raw)
        except ValueError:
            threshold = None

        if ticker and alert_type in ("price", "pct") and direction in ("above", "below") and threshold is not None and ticker in user_tickers:
            quote = finnhub_client.get_quote(ticker)
            baseline = quote.get("c") or None
            StockAlert.objects.create(
                user=request.user,
                ticker=ticker,
                alert_type=alert_type,
                direction=direction,
                threshold=threshold,
                baseline_price=baseline,
            )
        return redirect("alerts")

    user_alerts = StockAlert.objects.filter(user=request.user).order_by("triggered", "ticker")
    now = timezone.now()
    alert_rows = []
    for alert in user_alerts:
        status_label, status_detail = _build_alert_status(alert, now)
        alert_rows.append(
            {
                "alert": alert,
                "status_label": status_label,
                "status_detail": status_detail,
            }
        )

    return render(request, "stocks/alerts.html", {
        "alert_rows": alert_rows,
        "prefill_ticker": prefill_ticker,
        "user_tickers": user_tickers,
        "notification_notice": notification_notice,
        "push_subscription_count": PushSubscription.objects.filter(user=request.user).count(),
        "vapid_public_key": settings.VAPID_PUBLIC_KEY,
    })


# ---------------------------------------------------------------------------
# Push subscription
# ---------------------------------------------------------------------------

@login_required
@require_POST
@csrf_exempt
def subscribe_push(request):
    try:
        data = json.loads(request.body)
        endpoint = data["endpoint"]
        p256dh = data["keys"]["p256dh"]
        auth = data["keys"]["auth"]
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid"}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={"user": request.user, "p256dh": p256dh, "auth": auth},
    )
    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Live price API
# ---------------------------------------------------------------------------

@login_required
def price_api(request, ticker):
    quote = finnhub_client.get_quote(ticker.upper())
    return JsonResponse(quote)


# ---------------------------------------------------------------------------
# Service worker
# ---------------------------------------------------------------------------

def service_worker(request):
    sw_path = settings.BASE_DIR / "static" / "sw.js"
    with open(sw_path, "rb") as f:
        content = f.read()
    response = HttpResponse(content, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
