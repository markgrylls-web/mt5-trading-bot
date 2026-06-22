#!/usr/bin/env python3
"""
MT5 Automated Trading Bot - USDCAD
Main bot engine with EMA, FVG, Order Blocks, Support/Resistance, and Orderflow
"""

import sys

# Try to import real MT5, fall back to mock
try:
    import MetaTrader5 as mt5
except ImportError:
    import mock_mt5 as mt5
    sys.modules['MetaTrader5'] = mt5

import time
import pandas as pd
from datetime import datetime, timedelta
import signal

from utils import Utils
from logger import TradingLogger
from indicators import TechnicalIndicators
from analysis import MarketAnalysis
from trade_manager import TradeManager


class MT5TradingBot:
    def __init__(self, config_file='config.json'):
        """Initialize the trading bot"""
        self.config = Utils.load_config(config_file)
        
        if self.config is None:
            print("Failed to load configuration")
            sys.exit(1)
        
        if not Utils.validate_config(self.config):
            print("Configuration validation failed")
            sys.exit(1)
        
        self.logger = TradingLogger(self.config)
        self.running = True
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.log_info("MT5 Trading Bot initialized")
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals"""
        self.logger.log_info("Shutdown signal received. Closing positions...")
        self.running = False
    
    def start(self):
        """Start the trading bot"""
        try:
            # Connect to MT5
            if not Utils.connect_mt5(self.config):
                self.logger.log_error("Failed to connect to MT5")
                return False
            
            # Initialize modules
            trade_manager = TradeManager(self.config, self.logger)
            market_analysis = MarketAnalysis(self.config)
            
            # Print startup info
            account_info = trade_manager.get_account_info()
            Utils.print_startup_info(self.config, account_info)
            
            self.logger.log_info("Trading bot started successfully")
            
            # Main trading loop
            self._trading_loop(trade_manager, market_analysis)
            
        except Exception as e:
            self.logger.log_error(f"Fatal error: {str(e)}")
            return False
        finally:
            Utils.disconnect_mt5()
            self.logger.log_info("Trading bot stopped")
    
    def _trading_loop(self, trade_manager, market_analysis):
        """Main trading loop"""
        check_interval = 60  # Check every 60 seconds
        last_check = None
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check if we should analyze the market
                if last_check is None or (current_time - last_check).seconds >= check_interval:
                    last_check = current_time
                    
                    # Check trading hours
                    if not Utils.is_trading_hours(self.config):
                        self.logger.log_info(f"Outside trading hours - {current_time.strftime('%H:%M:%S')}")
                        time.sleep(check_interval)
                        continue
                    
                    # Get market data
                    df = self._get_market_data()
                    
                    if df is not None and len(df) > 0:
                        # Analyze market
                        signal_type, confidence, signal_details = market_analysis.generate_signals(df)
                        
                        # Log signal
                        self.logger.log_signal({
                            'symbol': self.config['trading']['symbol'],
                            'signal': signal_type,
                            'confidence': confidence,
                            'timestamp': current_time.isoformat(),
                            'details': signal_details
                        })
                        
                        # Execute trade if signal is strong
                        if signal_type != 'HOLD' and confidence >= 60:
                            self._execute_signal(
                                signal_type,
                                df,
                                market_analysis,
                                trade_manager
                            )
                    
                    # Update trailing stops
                    self._update_positions(trade_manager, df)
                    
                    # Log daily stats
                    daily_stats = trade_manager.get_daily_stats()
                    if daily_stats:
                        self.logger.log_info(
                            f"Daily Stats - Trades: {daily_stats['total_trades']}, "
                            f"Wins: {daily_stats['wins']}, "
                            f"Losses: {daily_stats['losses']}, "
                            f"Profit: ${daily_stats['total_profit']:.2f}, "
                            f"Win Rate: {daily_stats['win_rate']:.1f}%"
                        )
                
                time.sleep(5)  # Sleep for 5 seconds before checking again
            
            except Exception as e:
                self.logger.log_error(f"Error in trading loop: {str(e)}")
                time.sleep(check_interval)
    
    def _get_market_data(self):
        """Fetch market data from MT5"""
        try:
            symbol = self.config['trading']['symbol']
            timeframe = Utils.get_timeframe_enum(self.config['trading']['timeframe'])
            
            # Get last 100 candles
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
            
            if rates is None or len(rates) == 0:
                self.logger.log_error(f"Failed to get rates for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={
                'close': 'close',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'tick_volume': 'volume'
            })
            
            # Calculate indicators
            indicators = TechnicalIndicators(self.config)
            df = indicators.analyze_all(df)
            
            return df
        
        except Exception as e:
            self.logger.log_error(f"Error getting market data: {str(e)}")
            return None
    
    def _execute_signal(self, signal_type, df, market_analysis, trade_manager):
        """Execute trading signal"""
        try:
            account = trade_manager.get_account_info()
            if account is None:
                return
            
            # Get current price
            bid, ask = Utils.get_bid_ask(self.config['trading']['symbol'])
            if bid is None or ask is None:
                return
            
            entry_price = ask if signal_type == 'BUY' else bid
            
            # Calculate stop loss and take profit
            stop_loss = market_analysis.calculate_stop_loss(df, signal_type, entry_price)
            take_profit = market_analysis.calculate_take_profit(df, signal_type, entry_price, stop_loss)
            
            # Calculate position size
            position_size = market_analysis.get_position_size(
                account['balance'],
                entry_price,
                stop_loss,
                self.config['trading']['risk_percent']
            )
            
            # Format prices
            entry_price = Utils.format_price(entry_price, self.config['trading']['symbol'])
            stop_loss = Utils.format_price(stop_loss, self.config['trading']['symbol'])
            take_profit = Utils.format_price(take_profit, self.config['trading']['symbol'])
            position_size = round(position_size, 2)
            
            self.logger.log_info(
                f"Executing {signal_type} signal - "
                f"Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}, "
                f"Size: {position_size}"
            )
            
            # Open position
            trade_manager.open_position(
                signal_type,
                entry_price,
                stop_loss,
                take_profit,
                position_size
            )
        
        except Exception as e:
            self.logger.log_error(f"Error executing signal: {str(e)}")
    
    def _update_positions(self, trade_manager, df):
        """Update open positions (trailing stops, etc.)"""
        try:
            if df is None or len(df) == 0:
                return
            
            positions = trade_manager.get_positions()
            current_price = df.iloc[-1]['close']
            
            for pos in positions:
                # Update trailing stop
                if trade_manager.use_trailing_stop:
                    trade_manager.update_trailing_stop(pos['ticket'], current_price)
        
        except Exception as e:
            self.logger.log_error(f"Error updating positions: {str(e)}")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("Starting MT5 Automated Trading Bot")
    print("="*60 + "\n")
    
    bot = MT5TradingBot('config.json')
    bot.start()


if __name__ == '__main__':
    main()
