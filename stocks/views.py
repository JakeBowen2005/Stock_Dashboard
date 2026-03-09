from django.shortcuts import render

# Create your views here.

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

from Stock_class import Stock   # adjust import path if needed

def analyze(request):

    added_stocks = request.session.get("added_stocks", [])

    stock_summaries = []

    for ticker in added_stocks:
        try:
            stock = Stock(ticker)
            stock_summaries.append(stock.summary_dict())
        except Exception:
            pass  # skip invalid ticker for now

    return render(request, "stocks/dashboard.html", {
        "stocks": stock_summaries
    })
