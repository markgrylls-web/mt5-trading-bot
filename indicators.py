import numpy as np
import pandas as pd
import ta

class TechnicalIndicators:
    def __init__(self, config):
        self.config = config
        self.ema_fast = config['indicators']['ema_fast']
        self.ema_medium = config['indicators']['ema_medium']
        self.ema_slow = config['indicators']['ema_slow']
        self.sma_short = config['indicators']['sma_short']
        self.sma_long = config['indicators']['sma_long']
        self.fvg_lookback = config['indicators']['fvg_lookback']
        self.order_block_lookback = config['indicators']['order_block_lookback']
        self.sr_lookback = config['indicators']['support_resistance_lookback']
        self.orderflow_period = config['indicators']['orderflow_period']
        self.orderflow_threshold = config['indicators']['orderflow_threshold']
    
    def calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        return ta.trend.ema_indicator(close=prices, window=period)
    
    def calculate_sma(self, prices, period):
        """Calculate Simple Moving Average"""
        return ta.trend.sma_indicator(close=prices, window=period)
    
    def calculate_all_moving_averages(self, df):
        """Calculate all moving averages"""
        df['EMA_Fast'] = self.calculate_ema(df['close'], self.ema_fast)
        df['EMA_Medium'] = self.calculate_ema(df['close'], self.ema_medium)
        df['EMA_Slow'] = self.calculate_ema(df['close'], self.ema_slow)
        df['SMA_Short'] = self.calculate_sma(df['close'], self.sma_short)
        df['SMA_Long'] = self.calculate_sma(df['close'], self.sma_long)
        return df
    
    def detect_fvg(self, df):
        """Detect Fair Value Gaps (FVG)"""
        df['FVG_Bullish'] = 0
        df['FVG_Bearish'] = 0
        
        for i in range(2, len(df) - 1):
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                df['FVG_Bullish'].iloc[i] = 1
            if df['high'].iloc[i] < df['low'].iloc[i-2]:
                df['FVG_Bearish'].iloc[i] = 1
        
        return df
    
    def detect_order_blocks(self, df):
        """Detect Order Blocks"""
        df['Order_Block_Long'] = 0
        df['Order_Block_Short'] = 0
        
        lookback = self.order_block_lookback
        
        for i in range(lookback, len(df)):
            recent_high = df['high'].iloc[i-lookback:i].max()
            if df['close'].iloc[i] > df['open'].iloc[i] and df['high'].iloc[i] == recent_high:
                df['Order_Block_Long'].iloc[i] = 1
            
            recent_low = df['low'].iloc[i-lookback:i].min()
            if df['close'].iloc[i] < df['open'].iloc[i] and df['low'].iloc[i] == recent_low:
                df['Order_Block_Short'].iloc[i] = 1
        
        return df
    
    def calculate_support_resistance(self, df):
        """Calculate Support and Resistance Levels"""
        df['Support'] = 0.0
        df['Resistance'] = 0.0
        
        lookback = self.sr_lookback
        
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i]
            df['Support'].iloc[i] = window['low'].min()
            df['Resistance'].iloc[i] = window['high'].max()
        
        return df
    
    def calculate_orderflow(self, df):
        """Calculate Orderflow"""
        df['Volume_Direction'] = 0
        df['Orderflow_Strength'] = 0.0
        
        for i in range(1, len(df)):
            close_diff = df['close'].iloc[i] - df['close'].iloc[i-1]
            if close_diff > 0:
                df['Volume_Direction'].iloc[i] = 1
            elif close_diff < 0:
                df['Volume_Direction'].iloc[i] = -1
            else:
                df['Volume_Direction'].iloc[i] = 0
        
        df['Orderflow_Strength'] = df['Volume_Direction'].rolling(
            window=self.orderflow_period
        ).apply(lambda x: (x > 0).sum() / len(x) if len(x) > 0 else 0)
        
        return df
    
    def detect_ema_crossover(self, df):
        """Detect EMA crossovers"""
        df['EMA_Bullish_Cross'] = 0
        df['EMA_Bearish_Cross'] = 0
        
        for i in range(1, len(df)):
            if (df['EMA_Fast'].iloc[i-1] <= df['EMA_Medium'].iloc[i-1] and 
                df['EMA_Fast'].iloc[i] > df['EMA_Medium'].iloc[i]):
                df['EMA_Bullish_Cross'].iloc[i] = 1
            
            if (df['EMA_Fast'].iloc[i-1] >= df['EMA_Medium'].iloc[i-1] and 
                df['EMA_Fast'].iloc[i] < df['EMA_Medium'].iloc[i]):
                df['EMA_Bearish_Cross'].iloc[i] = 1
        
        return df
    
    def analyze_all(self, df):
        """Run all technical analysis"""
        df = self.calculate_all_moving_averages(df)
        df = self.detect_fvg(df)
        df = self.detect_order_blocks(df)
        df = self.calculate_support_resistance(df)
        df = self.calculate_orderflow(df)
        df = self.detect_ema_crossover(df)
        return df