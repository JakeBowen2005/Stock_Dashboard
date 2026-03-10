import pandas as pd

def daily_returns(data):
    data["Daily Returns"] = data["Close"].pct_change()
    return data

def basic_stats(data):
    daily_return = data["Daily Returns"].dropna()
    if daily_return.empty:
        return {
            "Annualized Return": 0.0,
            "Annualized Volatility": 0.0
        }

    # Total compounded return
    total_growth = (1 + daily_return).prod()

    # Number of years
    years = len(daily_return) / 252

    # True annualized return (geometric)
    annualized_return = total_growth ** (1 / years) - 1

    # Annualized volatility
    annualized_volatility = daily_return.std() * (252 ** 0.5)

    return {
        "Annualized Return": float(annualized_return),
        "Annualized Volatility": float(annualized_volatility)
    }

def price_to_earnings(history, financials):
    current_price = history["Close"].iloc[-1]
    try:
        eps = financials.loc["Basic EPS"].iloc[0]
    except (KeyError, IndexError):
        return None
    if not eps or eps == 0:
        return None
    return float(current_price / eps)

def total_return_percentage(history):
    end = history["Adj Close"].iloc[-1]
    start = history["Adj Close"].iloc[0]
    total_return = ((end/start)-1) * 100
    return float(total_return) 

def recent_return(data, days=21):
    data = data.copy()
    if len(data) < days:
        return None
    
    start = data["Adj Close"].iloc[-days]
    end = data["Adj Close"].iloc[-1]

    recent = (end/start) - 1
    return float(recent)

def moving_average(data, window=50):
    average = data["Adj Close"].rolling(window=window).mean()
    return average

def is_above_ma(data, window):
    ma = moving_average(data, window)
    current_price = data["Adj Close"].iloc[-1]
    current_ma = ma.iloc[-1]
    return current_price > current_ma

def year_high_low(data):
    high = data["Adj Close"].rolling(window=252).max().iloc[-1]
    low = data["Adj Close"].rolling(window=252).min().iloc[-1]
    current = data["Adj Close"].iloc[-1]

    return {
        "52W High": float(high),
        "52W Low": float(low),
        "Percent From High": float((current/high -1)),
        "Percent From Low": float((current/low - 1))
    }

def max_drawdown(data):
    current_prices = data["Adj Close"]

    cummax = current_prices.cummax()

    drawdown = (current_prices / cummax) - 1
    max_drawdown = drawdown.min()
    return float(max_drawdown)

def alltime_high(data):
    highest_price = data["Adj Close"].max()
    return highest_price

def cagr(data, years=None):
    prices = data["Adj Close"].dropna()
    
    if years:
        cutoff_date = prices.index[-1] - pd.DateOffset(years=years)
        prices = prices[prices.index >= cutoff_date]
        
        if len(prices) < 2:
            return None
    
    start_price = prices.iloc[0]
    end_price = prices.iloc[-1]
    
    # Calculate actual years between dates
    total_days = (prices.index[-1] - prices.index[0]).days
    total_years = total_days / 365.25
    
    cagr_value = (end_price / start_price) ** (1 / total_years) -1
    
    return float(cagr_value)


def _statement_value(statement_df, row_names):
    """
    Return the first non-null value for any candidate row name.
    """
    if statement_df is None or statement_df.empty:
        return None

    for row_name in row_names:
        if row_name in statement_df.index:
            series = statement_df.loc[row_name].dropna()
            if not series.empty:
                return float(series.iloc[0])
    return None


def return_on_equity(financials, balance_sheet):
    net_income = _statement_value(
        financials,
        [
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income Including Noncontrolling Interests",
        ],
    )
    total_equity = _statement_value(
        balance_sheet,
        [
            "Stockholders Equity",
            "Total Stockholder Equity",
            "Total Equity Gross Minority Interest",
            "Common Stock Equity",
        ],
    )

    if net_income is None or total_equity in (None, 0):
        return None
    return float(net_income / total_equity)


def debt_to_equity(balance_sheet):
    total_debt = _statement_value(
        balance_sheet,
        [
            "Total Debt",
            "Long Term Debt",
            "Long Term Debt And Capital Lease Obligation",
        ],
    )
    total_equity = _statement_value(
        balance_sheet,
        [
            "Stockholders Equity",
            "Total Stockholder Equity",
            "Total Equity Gross Minority Interest",
            "Common Stock Equity",
        ],
    )

    if total_debt is None or total_equity in (None, 0):
        return None
    return float(total_debt / total_equity)




