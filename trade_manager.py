import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

class TradeManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.symbol = config['trading']['symbol']
        self.timeframe = config['trading']['timeframe']
        self.risk_percent = config['trading']['risk_percent']
        self.use_trailing_stop = config['trading']['use_trailing_stop']
        self.trailing_stop_pips = config['trading']['trailing_stop_pips']
        self.max_positions = config['trading']['max_positions']
        self.daily_loss_limit = config['safety']['max_daily_loss_percent']
        self.max_consecutive_losses = config['safety']['max_consecutive_losses']
    
    def get_account_info(self):
        """Get account information"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.log_error("Failed to get account info")
                return None
            
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'free_margin': account_info.margin_free,
                'used_margin': account_info.margin_used,
                'margin_level': account_info.margin_level
            }
        except Exception as e:
            self.logger.log_error(f"Error getting account info: {str(e)}")
            return None
    
    def get_positions(self):
        """Get all open positions"""
        try:
            positions = mt5.positions_get(symbol=self.symbol)
            if positions is None or len(positions) == 0:
                return []
            
            return [
                {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'open_time': datetime.fromtimestamp(pos.time)
                }
                for pos in positions
            ]
        except Exception as e:
            self.logger.log_error(f"Error getting positions: {str(e)}")
            return []
    
    def open_position(self, signal_type, entry_price, stop_loss, take_profit, position_size):
        """Open a new position"""
        try:
            account = self.get_account_info()
            if account is None:
                return False
            
            positions = self.get_positions()
            if len(positions) >= self.max_positions:
                self.logger.log_warning(f"Max positions ({self.max_positions}) reached")
                return False
            
            order_type = mt5.ORDER_TYPE_BUY if signal_type == 'BUY' else mt5.ORDER_TYPE_SELL
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": position_size,
                "type": order_type,
                "price": entry_price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 20,
                "magic": 123456,
                "comment": f"Bot Signal: {signal_type}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.log_error(f"Order failed: {result.comment}")
                return False
            
            self.logger.log_trade({
                'type': signal_type,
                'symbol': self.symbol,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'signals': []
            })
            
            return True
        
        except Exception as e:
            self.logger.log_error(f"Error opening position: {str(e)}")
            return False
    
    def close_position(self, ticket, reason="Manual"):
        """Close a position"""
        try:
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                return False
            
            pos = positions[0]
            order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "price": mt5.symbol_info_tick(pos.symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(pos.symbol).ask,
                "deviation": 20,
                "magic": 123456,
                "comment": f"Close: {reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.log_error(f"Close order failed: {result.comment}")
                return False
            
            self.logger.log_close({
                'symbol': pos.symbol,
                'close_price': result.price,
                'pnl': pos.profit,
                'pnl_percent': (pos.profit / (pos.price_open * pos.volume)) * 100,
                'reason': reason
            })
            
            return True
        
        except Exception as e:
            self.logger.log_error(f"Error closing position: {str(e)}")
            return False
    
    def update_trailing_stop(self, ticket, current_price):
        """Update trailing stop loss"""
        try:
            if not self.use_trailing_stop:
                return True
            
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                return False
            
            pos = positions[0]
            
            if pos.type == 0:
                new_sl = current_price - (self.trailing_stop_pips * 0.0001)
                if new_sl > pos.sl:
                    return self._modify_position(ticket, new_sl, pos.tp)
            else:
                new_sl = current_price + (self.trailing_stop_pips * 0.0001)
                if new_sl < pos.sl:
                    return self._modify_position(ticket, new_sl, pos.tp)
            
            return True
        
        except Exception as e:
            self.logger.log_error(f"Error updating trailing stop: {str(e)}")
            return False
    
    def _modify_position(self, ticket, new_sl, new_tp):
        """Modify position's stop loss and take profit"""
        try:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": new_sl,
                "tp": new_tp,
            }
            
            result = mt5.order_send(request)
            return result.retcode == mt5.TRADE_RETCODE_DONE
        
        except Exception as e:
            self.logger.log_error(f"Error modifying position: {str(e)}")
            return False
    
    def get_daily_stats(self):
        """Get today's trading statistics"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            deals = mt5.history_deals_get(today_start, datetime.now())
            
            if deals is None or len(deals) == 0:
                return {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_profit': 0,
                    'win_rate': 0
                }
            
            wins = sum(1 for deal in deals if deal.profit > 0)
            losses = sum(1 for deal in deals if deal.profit < 0)
            total_profit = sum(deal.profit for deal in deals)
            
            return {
                'total_trades': len(deals),
                'wins': wins,
                'losses': losses,
                'total_profit': total_profit,
                'win_rate': (wins / len(deals) * 100) if len(deals) > 0 else 0
            }
        
        except Exception as e:
            self.logger.log_error(f"Error getting daily stats: {str(e)}")
            return None