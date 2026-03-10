from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.shortcuts import redirect, render

from stock_market_analyzer.Stock_class import Stock

from .forms import SignUpForm
from .models import WatchList, WatchListItem

DASHBOARD_CACHE_TTL = 15 * 60
DETAIL_CACHE_TTL = 30 * 60


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


def _get_or_create_user_watchlist(user):
    watchlist, _ = WatchList.objects.get_or_create(user=user)
    return watchlist


def _get_user_tickers(user):
    watchlist = _get_or_create_user_watchlist(user)
    return watchlist, list(
        watchlist.items.values_list("ticker", flat=True).order_by("ticker")
    )


def _get_cached_stock_summary(ticker, detailed=False):
    mode = "detail" if detailed else "dashboard"
    cache_key = f"stock_summary:{ticker}:{mode}:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    stock = Stock(
        ticker,
        include_profile=detailed,
        include_fundamentals=detailed,
    ).summary_dict()

    cache.set(cache_key, stock, DETAIL_CACHE_TTL if detailed else DASHBOARD_CACHE_TTL)
    return stock


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
            stock_summaries.append(_get_cached_stock_summary(ticker, detailed=False))
        except Exception as exc:
            print(f"[analyze] failed ticker {ticker}: {exc}")
            failed_tickers.append(ticker)

    return render(request, "stocks/dashboard.html", {
        "stocks": stock_summaries,
        "failed_tickers": failed_tickers,
    })


@login_required
def stock_detail(request, ticker):
    _get_or_create_user_watchlist(request.user)
    ticker = ticker.upper().strip()

    try:
        stock = _get_cached_stock_summary(ticker, detailed=True)
    except Exception as detail_exc:
        print(f"[detail] detailed fetch failed for {ticker}: {detail_exc}")
        try:
            # Fallback to lightweight data so user still gets a usable page.
            stock = _get_cached_stock_summary(ticker, detailed=False)
            stock["description"] = "Detailed company profile is temporarily unavailable due API limits."
            stock["sector"] = stock.get("sector") or "Data unavailable"
            stock["industry"] = stock.get("industry") or "Data unavailable"
        except Exception as fallback_exc:
            print(f"[detail] fallback fetch failed for {ticker}: {fallback_exc}")
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

    return render(request, "stocks/stock_detail.html", {
        "stock": stock,
        "signal": signal_snapshot,
        "market_cap_display": market_cap_display,
        "employees_display": employees_display,
        "short_term_chart": short_term_chart,
        "long_term_chart": long_term_chart,
        "risk_chart": risk_chart,
    })
