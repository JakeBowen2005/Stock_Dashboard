from . import data_loader
from . import stock_metrics
import pandas as pd
import time

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
        if self.price_history is None or self.price_history.empty:
            raise ValueError(f"No price data found for ticker: {ticker}")
        if "Adj Close" not in self.price_history.columns or "Close" not in self.price_history.columns:
            raise ValueError(f"Missing required price columns for ticker: {ticker}")

        self.price_history = stock_metrics.daily_returns(self.price_history)
        self.financials = data_loader.get_financials(self.ticker)
        self.actions = data_loader.get_actions(self.ticker)
        self.balance_sheet = data_loader.get_balance_sheet(self.ticker)

        # Current Price
        self.current_price = self.price_history["Adj Close"].iloc[-1]

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
        try:
            self.eps = float(self.financials.loc["Basic EPS"].iloc[0])
        except (KeyError, IndexError, TypeError):
            self.eps = None
        self.cagr_5y = stock_metrics.cagr(self.price_history, years=5)
        self.cagr_10y = stock_metrics.cagr(self.price_history, years=10)
        self.roe = stock_metrics.return_on_equity(self.financials, self.balance_sheet)
        self.debt_to_equity = stock_metrics.debt_to_equity(self.balance_sheet)

        # Company profile from yfinance info (with retries/fallbacks)
        info = {}
        for _ in range(2):
            try:
                info = self.ticker.info or {}
                if info:
                    break
            except Exception:
                info = {}
                time.sleep(0.3)

        if not info:
            try:
                info = self.ticker.get_info() or {}
            except Exception:
                info = {}

        self.company_name = info.get("longName") or info.get("shortName") or self.name
        self.sector = info.get("sector") or "Data unavailable"
        self.industry = info.get("industry") or "Data unavailable"
        self.market_cap = info.get("marketCap")
        self.description = info.get("longBusinessSummary") or f"{self.company_name} profile data is currently unavailable from the provider."
        self.employees = info.get("fullTimeEmployees")
        self.dividend_yield = info.get("dividendYield")
        self.beta = info.get("beta")
        self.forward_pe = info.get("forwardPE")
        self.price_to_book = info.get("priceToBook")


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

        def pct_or_none(value, digits=2):
            return round(value * 100, digits) if value is not None else None

        stock_dict = {
                    "name": self.name,
                    "current_price": round(self.current_price, 2),
                    "annual_return": round(self.basic_stats["Annualized Return"] * 100, 2),
                    "volatility": round(self.basic_stats["Annualized Volatility"] * 100, 2),
                    "52w_high": round(self.year_high, 2),
                    "52w_low": round(self.year_low, 2),
                    "percent_from_high": round(self.current_price_from_high * 100, 2),
                    "percent_from_low": round(self.current_price_from_low * 100, 2),
                    "one_week_return": pct_or_none(self.one_week_return),
                    "one_month_return": pct_or_none(self.one_month_return),
                    "three_month_return": pct_or_none(self.three_month_return),
                    "six_month_return": pct_or_none(self.six_month_return),
                    "pe_ratio": round_or_none(self.price_to_earnings),
                    "eps": round_or_none(self.eps),
                    "cagr_5y": pct_or_none(self.cagr_5y),
                    "cagr_10y": pct_or_none(self.cagr_10y),
                    "total_return_10y": round(self.total_return, 2),
                    "max_drawdown": round(self.max_drawdown * 100, 2),
                    "above_50ma": self.is_above50_ma,
                    "above_200ma": self.is_above200_ma,
                    "roe": round_or_none(self.roe * 100) if self.roe is not None else None,
                    "debt_to_equity": round_or_none(self.debt_to_equity),
                    "company_name": self.company_name,
                    "sector": self.sector,
                    "industry": self.industry,
                    "market_cap": self.market_cap,
                    "description": self.description,
                    "employees": self.employees,
                    "dividend_yield": round_or_none(self.dividend_yield * 100) if self.dividend_yield is not None else None,
                    "beta": round_or_none(self.beta),
                    "forward_pe": round_or_none(self.forward_pe),
                    "price_to_book": round_or_none(self.price_to_book),
        }
        return stock_dict
