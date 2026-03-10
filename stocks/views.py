from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from stock_market_analyzer.Stock_class import Stock

from .forms import SignUpForm
from .models import WatchList, WatchListItem


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
            notice = f"{ticker} is already added."
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

    for ticker in added_stocks:
        try:
            stock_summaries.append(Stock(ticker).summary_dict())
        except Exception:
            pass

    return render(request, "stocks/dashboard.html", {
        "stocks": stock_summaries
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
    return render(request, "stocks/stock_detail.html", {
        "stock": stock,
        "signal": signal_snapshot,
    })
