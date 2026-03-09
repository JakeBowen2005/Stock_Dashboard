class Portfolio:
    def __init__(self, stocks):
        """
        stocks: list of Stock objects
        """
        self.stocks = stocks
        self.tickers = [stock.ticker.ticker for stock in stocks]

    def best_performer(self):
        best = max(self.stocks, key=lambda s: s.total_return)
        return best.name

    def worst_performer(self):
        worst = min(self.stocks, key=lambda s: s.total_return)
        return worst.name

    def summary(self):
        print("Portfolio Summary")
        print("------------------")
        for stock in self.stocks:
            # print(f"{stock.ticker.ticker} Overall Performance")
            # print(f"  Current Price: {stock.current_price:.2f}")
            # print(f"  Annual Return: {stock.basic_stats['Annualized Return']:.2%}")
            # print(f"  Volatility: {stock.basic_stats['Annualized Volatility']:.2%}")
            # print(f"  52W High: {stock.year_high:.2f}")
            # print(f"  52W Low: {stock.year_low:.2f}")
            # print(f"  All time high: {stock.alltime_high:.2f}")
            # print("\n")
            # stock.recent_performance()
            # stock.longterm_performance()
            # print("\n")
            print(stock.summary_dict())