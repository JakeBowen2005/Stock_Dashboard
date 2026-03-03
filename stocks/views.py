from django.shortcuts import render, redirect

# Create your views here.

def home(request):
        # Initialize session storage for stocks if it doesn't exist
    if "added_stocks" not in request.session:
        request.session["added_stocks"] = []

    added_stocks = request.session["added_stocks"]
    if request.method == "POST":
        ticker = request.POST.get("ticker", "").strip().upper()

            # Validate input
        if ticker:
            if ticker not in added_stocks:
                if len(added_stocks) < 8:
                    added_stocks.append(ticker)
                    request.session["added_stocks"] = added_stocks

        return redirect("home")
    return render(request, "stocks/home.html", {
        "added_stocks" : added_stocks
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
