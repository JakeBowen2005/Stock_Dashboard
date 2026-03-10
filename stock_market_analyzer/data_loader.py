import pandas as pd
import yfinance as yf

def get_ticker(ticker):
    return yf.Ticker(ticker)

def is_valid_ticker(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return not hist.empty
    except Exception:
        return False

def get_history(ticker, period):
    try:
        history = ticker.history(period=period, auto_adjust=False)
    except Exception:
        history = pd.DataFrame()

    if history is None or history.empty:
        try:
            symbol = getattr(ticker, "ticker", "")
            history = yf.download(
                symbol,
                period=period,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        except Exception:
            history = pd.DataFrame()

    return history if history is not None else pd.DataFrame()

def get_financials(ticker):
    try:
        return ticker.financials
    except Exception:
        return pd.DataFrame()

def get_actions(ticker):
    try:
        return ticker.actions
    except Exception:
        return pd.DataFrame()

def get_balance_sheet(ticker):
    try:
        return ticker.balance_sheet
    except Exception:
        return pd.DataFrame()
