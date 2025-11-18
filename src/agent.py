import time
import sys
import pandas as pd
import threading
import configparser
from datetime import datetime, timezone

from api_client import AlpacaAPIClient
from strategy import PullbackStrategy
from scalping_strategy import ScalpingStrategy
from risk_manager import RiskManager
from order_executor import OrderExecutor
from logger import logger
from coingecko_scanner import CoinGeckoScanner
from technical_scanner import TechnicalScanner
from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit

class TradingAgent:
    def __init__(self, log_queue, config_queue, initial_config):
        self.log_queue = log_queue
        self.config_queue = config_queue
        self.config = initial_config
        self.is_running = threading.Event()
        self.agent_thread = None
        self._log("--- Trading Agent Initialized ---")

    def _log(self, message):
        logger.info(message)
        self.log_queue.put({'type': 'log', 'data': str(message)})

    def start(self):
        if self.agent_thread and self.agent_thread.is_alive():
            self._log("Agent is already running.")
            return
        self.is_running.set()
        self.agent_thread = threading.Thread(target=self._main_loop)
        self.agent_thread.start()
        self._log("--- Trading Agent Thread Started ---")

    def stop(self):
        self._log("--- Stopping Trading Agent ---")
        self.is_running.clear()
        if self.agent_thread:
            self.agent_thread.join()
        self._log("--- Trading Agent Thread Stopped ---")

    def _update_config(self):
        try:
            new_config = self.config_queue.get_nowait()
            self.config = new_config
            self._log("--- Configuration updated by GUI ---")
        except Exception:
            pass

    def _main_loop(self):
        client = AlpacaAPIClient()
        executor = OrderExecutor(client)
        
        strategy_map = {"pullback": PullbackStrategy, "scalping": ScalpingStrategy}
        
        while self.is_running.is_set():
            try:
                self._update_config()
                
                risk_manager = RiskManager(client, self.config)
                
                self._log(f"\n--- New Cycle: {pd.Timestamp.now(tz='UTC')} ---")

                strategy_name = self.config.get('main', 'strategy_to_use', fallback='scalping')
                StrategyClass = strategy_map.get(strategy_name, ScalpingStrategy)
                
                symbols_str = self.config.get('main', 'symbols_to_trade', fallback='BTC/USD,ETH/USD')
                symbols_to_analyze = [s.strip().upper() for s in symbols_str.split(',')]
                
                self._log(f"Using Strategy: {strategy_name}, Analyzing: {', '.join(symbols_to_analyze)}")

                open_positions = client.api.list_positions()
                open_orders = client.api.list_orders(status='open')
                for p in open_positions:
                    if '/' not in p.symbol:
                        p.symbol = f"{p.symbol[:-3]}/{p.symbol[-3:]}"
                open_order_symbols = {o.symbol for o in open_orders}
                open_position_symbols = {p.symbol for p in open_positions}

                tf_map = {"15Min": TimeFrame(15, TimeFrameUnit.Minute), "5Min": TimeFrame(5, TimeFrameUnit.Minute), "1Hour": TimeFrame.Hour}
                timeframe = tf_map.get(self.config.get('main', 'timeframe', fallback='5Min'))
                
                # MANAGE OPEN POSITIONS
                for position in open_positions:
                    self._log(f"Managing open position for {position.symbol}...")
                    end_date = pd.Timestamp.now(tz='UTC')
                    start_date = end_date - pd.Timedelta(days=3)
                    data = client.get_crypto_bars([position.symbol], timeframe, start_date.isoformat(), end_date.isoformat())
                    if data is None or data.empty: continue

                    params = dict(self.config.items(f"{strategy_name}_strategy"))
                    for k, v in params.items():
                        if any(sub in k for sub in ['len', 'oversold', 'overbought', '_k', '_d']): params[k] = int(v)
                    
                    strategy = StrategyClass(data[data['symbol'] == position.symbol], params)
                    if strategy.df.empty: continue

                    signal = strategy.generate_signal(position=position)
                    self._log(f"Signal for open position {position.symbol}: {signal}")

                    if signal in ['EXIT_LONG', 'EXIT_SHORT']:
                        self._log(f"!!! {signal} SIGNAL DETECTED for {position.symbol} !!!")
                        executor.close_position(position.symbol)

                # LOOK FOR NEW ENTRIES
                if risk_manager.can_open_new_trade():
                    for symbol in symbols_to_analyze:
                        if symbol in open_position_symbols or symbol in open_order_symbols: continue
                        if not self.is_running.is_set(): break
                        
                        self._log(f"Analyzing {symbol} for new entry...")
                        end_date = pd.Timestamp.now(tz='UTC')
                        start_date = end_date - pd.Timedelta(days=3)
                        data = client.get_crypto_bars([symbol], timeframe, start_date.isoformat(), end_date.isoformat())
                        if data is None or data.empty: continue
                        
                        params = dict(self.config.items(f"{strategy_name}_strategy"))
                        for k, v in params.items():
                            if any(sub in k for sub in ['len', 'oversold', 'overbought', '_k', '_d']): params[k] = int(v)

                        strategy = StrategyClass(data[data['symbol'] == symbol], params)
                        if strategy.df.empty: continue

                        signal = strategy.generate_signal(position=None)
                        self._log(f"Signal for new entry {symbol}: {signal}")

                        if signal == 'BUY': # --- LONG-ONLY LOGIC ---
                            self._log(f"!!! {signal} SIGNAL DETECTED for {symbol} !!!")
                            last_atr = strategy.df['atr'].iloc[-1]
                            entry_price = strategy.df['close'].iloc[-1]
                            side = 'buy'
                            stop_loss_price = entry_price - (1.5 * last_atr)
                            quantity = risk_manager.calculate_position_size(entry_price, stop_loss_price)
                            if quantity > 0:
                                executor.place_order_with_sl(symbol, quantity, side, f"{stop_loss_price:.2f}")
                
                # Update GUI
                account_info = client.get_account_info()
                positions = client.api.list_positions()
                if account_info:
                    kpi_data = {
                        "Portfolio Value": f"${float(account_info.portfolio_value):,.2f}",
                        "Buying Power": f"${float(account_info.buying_power):,.2f}",
                        "Open Positions": str(len(positions))
                    }
                    self.log_queue.put({'type': 'kpi_update', 'data': kpi_data})
                    self.log_queue.put({'type': 'positions_update', 'data': positions})

                self._log("Cycle complete. Waiting for next scan.")
                time.sleep(int(self.config.get('main', 'poll_interval_seconds', fallback=60)))

            except Exception as e:
                self._log(f"An error occurred in the main loop: {e}")
                time.sleep(30)
