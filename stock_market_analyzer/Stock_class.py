from . import data_loader
from . import stock_metrics
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_rows", None)

class Stock:
    def __init__(self, ticker):
        # Big Data Sets
        self.name = ticker
        self.ticker = data_loader.get_ticker(ticker)
        self.price_history = data_loader.get_history(self.ticker, '10y')
        self.price_history = stock_metrics.daily_returns(self.price_history)
        self.financials = data_loader.get_financials(self.ticker)
        self.actions = data_loader.get_actions(self.ticker)
        self.balance_sheet = data_loader.get_balance_sheet(self.ticker)

        # Current Price
        self.current_price = self.price_history["Adj Close"].iloc[-1]

        #Validate ticker
        if self.price_history.empty:
            raise ValueError(f"No price data found for ticker: {ticker}")

        #Computed Metrics
        self.basic_stats = stock_metrics.basic_stats(self.price_history)
        self.price_to_earnings = stock_metrics.price_to_earnings(self.price_history, self.financials)
        self.total_return = stock_metrics.total_return_percentage(self.price_history)
        self.one_week_return = stock_metrics.recent_return(self.price_history, days=5)
        self.one_month_return = stock_metrics.recent_return(self.price_history, days=21)
        self.three_month_return = stock_metrics.recent_return(self.price_history, days=63)
        self.six_month_return = stock_metrics.recent_return(self.price_history, days=126)
        self.is_above50_ma = stock_metrics.is_above_ma(self.price_history, window=50)
        self.is_above200_ma = stock_metrics.is_above_ma(self.price_history, window=200)
        self.year_high_low_stats = stock_metrics.year_high_low(self.price_history)
        self.year_high = self.year_high_low_stats["52W High"]
        self.year_low = self.year_high_low_stats["52W Low"]
        self.current_price_from_high = self.year_high_low_stats["Percent From High"]
        self.current_price_from_low = self.year_high_low_stats["Percent From Low"]
        self.max_drawdown = stock_metrics.max_drawdown(self.price_history)
        self.alltime_high = stock_metrics.alltime_high(self.price_history)
        self.eps = self.financials.loc["Basic EPS"].iloc[0]
        self.cagr_5y = stock_metrics.cagr(self.price_history, years=5)
        self.cagr_10y = stock_metrics.cagr(self.price_history, years=10)
        self.roe = stock_metrics.return_on_equity(self.financials, self.balance_sheet)
        self.debt_to_equity = stock_metrics.debt_to_equity(self.balance_sheet)


    #Recent performace
    def recent_performance(self):
        print(f"{self.name} Recent Performance")
        print(f"  One Week Return: {self.one_week_return:.2f}%")
        print(f"  One Month Return: {self.one_month_return:.2f}%")
        print(f"  Three Month Return: {self.three_month_return:.2f}%")
        print(f"  Price to Earnings: {self.price_to_earnings:.2f}")
        print(f"  Earning per share: {self.eps}")
        print("  ------------------")


    def longterm_performance(self):
        print(f"{self.name} Long Term Perfomance")
        print(f"  5Y CAGR: {self.cagr_5y * 100:.2f}%")
        print(f"  10Y CAGR: {self.cagr_10y * 100:.2f}%")
        print(f"  10 Year Total Return: {self.total_return:.2f}")
        print(f"  Max Drawdown: {self.max_drawdown:.2f}%")

    def summary_dict(self):
        def round_or_none(value, digits=2):
            return round(value, digits) if value is not None else None

        stock_dict = {
                    "name": self.name,
                    "current_price": round(self.current_price, 2),
                    "annual_return": round(self.basic_stats["Annualized Return"] * 100, 2),
                    "volatility": round(self.basic_stats["Annualized Volatility"] * 100, 2),
                    "52w_high": round(self.year_high, 2),
                    "52w_low": round(self.year_low, 2),
                    "percent_from_high": round(self.current_price_from_high * 100, 2),
                    "percent_from_low": round(self.current_price_from_low * 100, 2),
                    "one_week_return": round(self.one_week_return * 100, 2),
                    "one_month_return": round(self.one_month_return * 100, 2),
                    "three_month_return": round(self.three_month_return * 100, 2),
                    "six_month_return": round(self.six_month_return * 100, 2),
                    "pe_ratio": round(self.price_to_earnings, 2),
                    "eps": round(self.eps, 2),
                    "cagr_5y": round(self.cagr_5y * 100, 2),
                    "cagr_10y": round(self.cagr_10y * 100, 2),
                    "total_return_10y": round(self.total_return, 2),
                    "max_drawdown": round(self.max_drawdown * 100, 2),
                    "above_50ma": self.is_above50_ma,
                    "above_200ma": self.is_above200_ma,
                    "roe": round_or_none(self.roe * 100) if self.roe is not None else None,
                    "debt_to_equity": round_or_none(self.debt_to_equity),
        }
        return stock_dict
