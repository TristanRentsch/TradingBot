import numpy as np

class RetrospectiveOrangeChicken(QCAlgorithm):

    def Initialize(self):
        self.SetCash(1000000)
        
        self.SetStartDate(2015, 9, 1)
        self.SetEndDate(2021, 1, 1)
        
        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol
        
        self.lookback = 20
        
        self.ceiling, self.floor = 20, 10
        
        self.initialStopRisk = 0.95
        self.trailingStopRisk = 0.93
        
        # Call EveryMarketOpen method every day 20 min after market opens
        self.Schedule.On(self.DateRules.EveryDay(self.symbol), \
                self.TimeRules.AfterMarketOpen(self.symbol, 20), \
                Action(self.EveryMarketOpen))


    def OnData(self, data):
        self.Plot("Data Chart", self.symbol, self.Securities[self.symbol].Close)
        
    def EveryMarketOpen(self):
        
        # Calculate lookback length by comparing 
        # today's volitility to yesterday's
        closingPrice = self.History(self.symbol, 31, Resolution.Daily)["close"]
        currVol = np.std(closingPrice[1:31])
        yesterVol = np.std(closingPrice[0:30])
        delta = (currVol - yesterVol) / currVol
        self.lookback = round(self.lookback * (1 + delta))
        
        # Make sure lookback is within bounds
        if self.lookback > self.ceiling:
            self.lookback = self.ceiling
        elif self.lookback < self.floor:
            self.lookback = self.floor
            
        
        # Get daily price highs within lookback
        self.high = self.History(self.symbol, self.lookback, Resolution.Daily)["high"]
                        
                        
        # === Buying ===
        
        # Make sure that we aren't invested and that a breakout is happening
        if not self.Securities[self.symbol].Invested and \
                self.Securities[self.symbol].Close >= max(self.high[:-1]):
            # Buy at market price
            self.SetHoldings(self.symbol, 1)
            self.breakoutlvl = max(self.high[:-1])
            self.highestPrice = self.breakoutlvl
        
        
        # === Trailing Stop Loss (Selling) ===
        
        # Make sure we have an open position
        if self.Securities[self.symbol].Invested:
            
            # Send out stop loss if we haven't already
            if not self.Transactions.GetOpenOrders(self.symbol):
                self.stopMarketTicket = self.StopMarketOrder(self.symbol, \
                        -self.Portfolio[self.symbol].Quantity, \
                        self.initialStopRisk * self.breakoutlvl)
            
            # Rise stop loss if new high was made
            if self.Securities[self.symbol].Close > self.highestPrice and \
                    self.initialStopRisk * self.breakoutlvl < self.Securities[self.symbol].Close * self.trailingStopRisk:

                self.highestPrice = self.Securities[self.symbol].Close
                updateFields = UpdateOrderFields()
                updateFields.StopPrice = self.Securities[self.symbol].Close * self.trailingStopRisk
                self.stopMarketTicket.Update(updateFields)
                
                # Print the new stop price
                self.Debug(updateFields.StopPrice)    
            
            self.Plot("Data Chart", "Stop Price", self.stopMarketTicket.Get(OrderField.StopPrice))
