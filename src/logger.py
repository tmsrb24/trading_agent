import csv
import os
from datetime import datetime

class TradeLogger:
    def __init__(self, filename='trades.csv'):
        self.filename = filename
        self.file_exists = os.path.isfile(self.filename)
        self.fieldnames = [
            'timestamp', 'symbol', 'side', 'quantity', 
            'entry_price', 'stop_loss', 'take_profit', 'pnl', 'exit_reason'
        ]
        if not self.file_exists:
            self._create_header()

    def _create_header(self):
        with open(self.filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writeheader()

    def log_trade(self, symbol, side, quantity, entry_price, stop_loss, take_profit):
        """Logs the details of an opened trade."""
        with open(self.filename, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writerow({
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'pnl': '', # To be filled on close
                'exit_reason': '' # To be filled on close
            })
        print(f"LOGGED: New {side} trade for {symbol}.")

    # In a real implementation, you would also have a method like:
    # def log_trade_close(self, order_id, pnl, reason):
    #     # This would find the trade by ID and update the PnL and exit_reason fields.
    #     pass
