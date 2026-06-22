import json
import os
from datetime import datetime
import MetaTrader5 as mt5

class Utils:
    @staticmethod
    def load_config(config_file='config.json'):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            print(f"Config file '{config_file}' not found!")
            return None
        except json.JSONDecodeError:
            print(f"Invalid JSON in config file '{config_file}'")
            return None
    
    @staticmethod
    def validate_config(config):
        """Validate configuration file"""
        required_keys = {
            'mt5': ['login', 'password', 'server'],
            'trading': ['symbol', 'timeframe', 'risk_percent'],
            'indicators': ['ema_fast', 'ema_medium', 'ema_slow'],
        }
        
        for section, keys in required_keys.items():
            if section not in config:
                print(f"Missing section: {section}")
                return False
            
            for key in keys:
                if key not in config[section]:
                    print(f"Missing key: {section}.{key}")
                    return False
        
        return True
    
    @staticmethod
    def connect_mt5(config):
        """Connect to MetaTrader 5"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                print("Failed to initialize MT5")
                return False
            
            # Login
            login_result = mt5.login(
                login=config['mt5']['login'],
                password=config['mt5']['password'],
                server=config['mt5']['server']
            )
            
            if not login_result:
                print(f"Failed to login to MT5: {mt5.last_error()}")
                return False
            
            print(f"Connected to MT5 - Account: {config['mt5']['login']}")
            return True
        
        except Exception as e:
            print(f"Error connecting to MT5: {str(e)}")
            return False
    
    @staticmethod
    def disconnect_mt5():
        """Disconnect from MetaTrader 5"""
        try:
            mt5.shutdown()
            print("Disconnected from MT5")
            return True
        except Exception as e:
            print(f"Error disconnecting from MT5: {str(e)}")
            return False
    
    @staticmethod
    def get_timeframe_enum(timeframe_str):
        """Convert timeframe string to MT5 enum"""
        timeframes = {
            'M1': mt5.TIMEFRAME_M1,
            'M2': mt5.TIMEFRAME_M2,
            'M3': mt5.TIMEFRAME_M3,
            'M4': mt5.TIMEFRAME_M4,
            'M5': mt5.TIMEFRAME_M5,
            'M6': mt5.TIMEFRAME_M6,
            'M10': mt5.TIMEFRAME_M10,
            'M12': mt5.TIMEFRAME_M12,
            'M15': mt5.TIMEFRAME_M15,
            'M20': mt5.TIMEFRAME_M20,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H2': mt5.TIMEFRAME_H2,
            'H3': mt5.TIMEFRAME_H3,
            'H4': mt5.TIMEFRAME_H4,
            'H6': mt5.TIMEFRAME_H6,
            'H8': mt5.TIMEFRAME_H8,
            'H12': mt5.TIMEFRAME_H12,
            'D1': mt5.TIMEFRAME_D1,
            'W1': mt5.TIMEFRAME_W1,
            'MN1': mt5.TIMEFRAME_MN1,
        }
        
        return timeframes.get(timeframe_str, mt5.TIMEFRAME_M15)
    
    @staticmethod
    def is_trading_hours(config):
        """Check if current time is within trading hours"""
        if not config['trading_hours']['enabled']:
            return True
        
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        current_time = current_hour * 60 + current_minute
        
        start_time = config['trading_hours']['start_hour'] * 60 + config['trading_hours']['start_minute']
        end_time = config['trading_hours']['end_hour'] * 60 + config['trading_hours']['end_minute']
        
        return start_time <= current_time <= end_time
    
    @staticmethod
    def get_bid_ask(symbol):
        """Get current bid and ask prices"""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None, None
            
            return tick.bid, tick.ask
        except Exception as e:
            print(f"Error getting bid/ask: {str(e)}")
            return None, None
    
    @staticmethod
    def pips_to_points(pips, symbol):
        """Convert pips to points for the given symbol"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return None
            
            # Most forex pairs: 1 pip = 0.0001 (4 decimal places)
            # JPY pairs: 1 pip = 0.01 (2 decimal places)
            if 'JPY' in symbol:
                return pips * 0.01
            else:
                return pips * 0.0001
        except Exception as e:
            print(f"Error converting pips to points: {str(e)}")
            return None
    
    @staticmethod
    def format_price(price, symbol):
        """Format price according to symbol's decimal places"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return price
            
            digits = symbol_info.digits
            return round(price, digits)
        except Exception as e:
            print(f"Error formatting price: {str(e)}")
            return price
    
    @staticmethod
    def print_startup_info(config, account_info):
        """Print startup information"""
        print("\n" + "="*60)
        print("MT5 AUTOMATED TRADING BOT - USDCAD")
        print("="*60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nConfiguration:")
        print(f"  Symbol: {config['trading']['symbol']}")
        print(f"  Timeframe: {config['trading']['timeframe']}")
        print(f"  Risk per trade: {config['trading']['risk_percent']}%")
        print(f"  Max positions: {config['trading']['max_positions']}")
        print(f"\nAccount Information:")
        if account_info:
            print(f"  Balance: ${account_info['balance']:.2f}")
            print(f"  Equity: ${account_info['equity']:.2f}")
            print(f"  Free Margin: ${account_info['free_margin']:.2f}")
            print(f"  Margin Level: {account_info['margin_level']:.2f}%")
        print("\n" + "="*60 + "\n")
