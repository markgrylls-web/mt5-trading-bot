import logging
import json
from datetime import datetime
from pathlib import Path

class TradingLogger:
    def __init__(self, config):
        self.config = config
        self.log_file = config['logging']['log_file']
        self.console_output = config['logging']['console_output']
        self.level = config['logging']['level']
        
        # Create logger
        self.logger = logging.getLogger('MT5Bot')
        self.logger.setLevel(getattr(logging, self.level))
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(getattr(logging, self.level))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.level))
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        if self.console_output:
            self.logger.addHandler(console_handler)
    
    def log_trade(self, trade_data):
        """Log a trade execution"""
        trade_log = {
            'timestamp': datetime.now().isoformat(),
            'type': trade_data.get('type', 'N/A'),
            'symbol': trade_data.get('symbol', 'N/A'),
            'entry_price': trade_data.get('entry_price', 0),
            'stop_loss': trade_data.get('stop_loss', 0),
            'take_profit': trade_data.get('take_profit', 0),
            'position_size': trade_data.get('position_size', 0),
            'signals': trade_data.get('signals', [])
        }
        self.logger.info(f"TRADE EXECUTED: {json.dumps(trade_log)}")
    
    def log_close(self, close_data):
        """Log a trade closure"""
        close_log = {
            'timestamp': datetime.now().isoformat(),
            'symbol': close_data.get('symbol', 'N/A'),
            'close_price': close_data.get('close_price', 0),
            'pnl': close_data.get('pnl', 0),
            'pnl_percent': close_data.get('pnl_percent', 0),
            'reason': close_data.get('reason', 'N/A')
        }
        self.logger.info(f"POSITION CLOSED: {json.dumps(close_log)}")
    
    def log_signal(self, signal_data):
        """Log a trading signal"""
        self.logger.info(f"SIGNAL: {json.dumps(signal_data)}")
    
    def log_error(self, error_msg):
        """Log an error"""
        self.logger.error(f"ERROR: {error_msg}")
    
    def log_info(self, info_msg):
        """Log general info"""
        self.logger.info(info_msg)
    
    def log_warning(self, warning_msg):
        """Log a warning"""
        self.logger.warning(f"WARNING: {warning_msg}")