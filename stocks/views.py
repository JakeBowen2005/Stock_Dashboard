from django.shortcuts import render

from stock_market_analyzer.Stock_class import Stock


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


def home(request):
    notice = ""

    if request.method == "GET":
        request.session["added_stocks"] = []
        return render(request, "stocks/home.html", {
            "added_stocks": [],
            "notice": notice,
        })

    added_stocks = request.session.get("added_stocks", [])
    action = request.POST.get("action", "add")
    ticker = request.POST.get("ticker", "").strip().upper()

    if action == "remove":
        if ticker in added_stocks:
            added_stocks.remove(ticker)
            notice = f"Removed {ticker}."
    else:
        if not ticker:
            notice = "Enter a ticker symbol."
        elif ticker in added_stocks:
            notice = f"{ticker} is already added."
        elif len(added_stocks) >= 8:
            notice = "You can add up to 8 stocks."
        else:
            added_stocks.append(ticker)
            notice = f"Added {ticker}."

    request.session["added_stocks"] = added_stocks
    return render(request, "stocks/home.html", {
        "added_stocks": added_stocks,
        "notice": notice,
    })


def analyze(request):
    added_stocks = request.session.get("added_stocks", [])
    stock_summaries = []

    for ticker in added_stocks:
        try:
            stock_summaries.append(Stock(ticker).summary_dict())
        except Exception:
            pass

    return render(request, "stocks/dashboard.html", {
        "stocks": stock_summaries
    })


def stock_detail(request, ticker):
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
