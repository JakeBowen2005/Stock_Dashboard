import data_loader
import pandas as pd
import stock_metrics
import Stock_class
import Portfolio_class
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)











# ticker = input("Enter stock ticker you want information on: ")
# period = input("Enter time period you want (1d, 5d, 1mo, 6mo, 1y): ")
user_input = input("List the tickers you want Stock Anaylsis on: ")
tickers = user_input.strip().upper().split()
stocks = []

for tick in tickers:
    try:
        stocks.append(Stock_class.Stock(tick))
    except ValueError:
        print(f"Skipping invalid ticker: {tick}")
portfolio = Portfolio_class.Portfolio(stocks)
print(portfolio.summary())
