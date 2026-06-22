import numpy as np
import pandas as pd
from indicators import TechnicalIndicators

class MarketAnalysis:
    def __init__(self, config):
        self.config = config
        self.indicators = TechnicalIndicators(config)
        self.orderflow_threshold = config['indicators']['orderflow_threshold']
    
    def generate_signals(self, df):
        """Generate trading signals based on multiple indicators"""
        if df is None or len(df) < 50:
            return 'HOLD', 0, {}
        
        current = df.iloc[-1]
        
        signal_details = {
            'ema_signal': self._check_ema_signal(df),
            'fvg_signal': self._check_fvg_signal(df),
            'order_block_signal': self._check_order_block_signal(df),
            'support_resistance_signal': self._check_sr_signal(df),
            'orderflow_signal': self._check_orderflow_signal(df),
            'price_action_signal': self._check_price_action(df)
        }
        
        buy_signals = sum(1 for v in signal_details.values() if v == 'BUY')
        sell_signals = sum(1 for v in signal_details.values() if v == 'SELL')
        
        total_signals = len(signal_details)
        
        if buy_signals >= 3:
            confidence = int((buy_signals / total_signals) * 100)
            return 'BUY', confidence, signal_details
        elif sell_signals >= 3:
            confidence = int((sell_signals / total_signals) * 100)
            return 'SELL', confidence, signal_details
        else:
            confidence = 0
            return 'HOLD', confidence, signal_details
    
    def _check_ema_signal(self, df):
        """Check EMA crossover signals"""
        current = df.iloc[-1]
        
        if (current['EMA_Fast'] > current['EMA_Medium'] > current['EMA_Slow']):
            return 'BUY'
        elif (current['EMA_Fast'] < current['EMA_Medium'] < current['EMA_Slow']):
            return 'SELL'
        else:
            return 'HOLD'
    
    def _check_fvg_signal(self, df):
        """Check Fair Value Gap signals"""
        current = df.iloc[-1]
        
        if current['FVG_Bullish'] == 1:
            return 'BUY'
        elif current['FVG_Bearish'] == 1:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _check_order_block_signal(self, df):
        """Check Order Block signals"""
        current = df.iloc[-1]
        
        if current['Order_Block_Long'] == 1:
            return 'BUY'
        elif current['Order_Block_Short'] == 1:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _check_sr_signal(self, df):
        """Check Support/Resistance signals"""
        current = df.iloc[-1]
        
        if current['close'] > current['Resistance'] * 0.98 and current['close'] < current['Resistance']:
            return 'SELL'
        elif current['close'] < current['Support'] * 1.02 and current['close'] > current['Support']:
            return 'BUY'
        else:
            return 'HOLD'
    
    def _check_orderflow_signal(self, df):
        """Check Orderflow signals"""
        current = df.iloc[-1]
        
        if pd.isna(current['Orderflow_Strength']):
            return 'HOLD'
        
        if current['Orderflow_Strength'] > self.orderflow_threshold:
            return 'BUY'
        elif current['Orderflow_Strength'] < (1 - self.orderflow_threshold):
            return 'SELL'
        else:
            return 'HOLD'
    
    def _check_price_action(self, df):
        """Check price action signals"""
        current = df.iloc[-1]
        
        if (current['close'] > current['open'] and 
            current['close'] > current['EMA_Fast']):
            return 'BUY'
        elif (current['close'] < current['open'] and 
              current['close'] < current['EMA_Fast']):
            return 'SELL'
        else:
            return 'HOLD'
    
    def calculate_entry_price(self, df, signal_type):
        """Calculate optimal entry price"""
        current = df.iloc[-1]
        return current['close']
    
    def calculate_stop_loss(self, df, signal_type, entry_price):
        """Calculate stop loss"""
        lookback = 20
        recent_data = df.tail(lookback)
        
        if signal_type == 'BUY':
            stop_loss = recent_data['low'].min() - (recent_data['close'].std() * 0.5)
        else:
            stop_loss = recent_data['high'].max() + (recent_data['close'].std() * 0.5)
        
        return stop_loss
    
    def calculate_take_profit(self, df, signal_type, entry_price, stop_loss):
        """Calculate take profit"""
        risk = abs(entry_price - stop_loss)
        reward_ratio = 2.0
        
        if signal_type == 'BUY':
            take_profit = entry_price + (risk * reward_ratio)
        else:
            take_profit = entry_price - (risk * reward_ratio)
        
        return take_profit
    
    def get_position_size(self, account_balance, entry_price, stop_loss, risk_percent):
        """Calculate position size"""
        risk_amount = account_balance * (risk_percent / 100)
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk > 0:
            position_size = risk_amount / price_risk
        else:
            position_size = 0
        
        return position_size