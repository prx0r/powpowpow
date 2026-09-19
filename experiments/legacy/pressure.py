"""
Pressure Equation — The Core PowPowPow Metric
Calculates structural pressure + microstructure triggers.
"""

import json
import os
import sys
import numpy as np
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from ofi import OFICalculator

class PressureEquation:
    """
    Calculates the pressure balance for a chain.
    
    Pressure Balance = Buy Absorption / (Miner Sell Pressure + Other Aggressive Sells)
    """
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.ofi_calc = OFICalculator()
        self.state = {
            'slow': {},  # Hours/days
            'fast': {},  # Milliseconds/minutes
        }
        self.history = []
    
    def update_slow_state(self, data):
        """Update slow-moving state variables."""
        self.state['slow'].update(data)
    
    def update_fast_state(self, depth_bids, depth_asks, trades=None, timestamp=None):
        """Update fast-moving state variables from L2 data."""
        # Update OFI calculator
        ofi_result = self.ofi_calc.update_depth(depth_bids, depth_asks, timestamp)
        
        # Get book metrics
        book_metrics = self.ofi_calc.calculate_book_metrics()
        
        # Get multi-level OFI
        multi_level_ofi = self.ofi_calc.calculate_multi_level_ofi([1, 5, 10, 25])
        
        # Get trade OFI
        trade_ofi = self.ofi_calc.calculate_trade_ofi(window_seconds=60)
        
        # Record trades
        if trades:
            for trade in trades:
                self.ofi_calc.record_trade(
                    trade.get('price', 0),
                    trade.get('amount', 0),
                    trade.get('side', 'unknown'),
                    timestamp
                )
        
        # Update fast state
        self.state['fast'] = {
            'timestamp': timestamp or datetime.now().isoformat(),
            **ofi_result,
            **book_metrics,
            **multi_level_ofi,
            **trade_ofi,
        }
        
        return self.state['fast']
    
    def calculate_creation_pressure(self):
        """Calculate creation pressure from emission data."""
        slow = self.state['slow']
        
        emission_usd_day = slow.get('emission_usd_day', 0)
        bid_depth_5pct = self.state['fast'].get('bid_depth_5pct', 1)
        
        creation_pressure = emission_usd_day / bid_depth_5pct if bid_depth_5pct > 0 else 0
        
        return {
            'emission_usd_day': emission_usd_day,
            'bid_depth_5pct': bid_depth_5pct,
            'creation_pressure': creation_pressure,
        }
    
    def calculate_realization_pressure(self):
        """Calculate miner realization pressure."""
        slow = self.state['slow']
        fast = self.state['fast']
        
        miner_exchange_flow = slow.get('miner_exchange_flow_usd_day', 0)
        emission_usd = slow.get('emission_usd_day', 1)
        
        # Miner realization ratio
        realization_ratio = miner_exchange_flow / emission_usd if emission_usd > 0 else 0
        
        # Liquidity-adjusted sell pressure
        sell_notional = miner_exchange_flow / 24  # Hourly
        bid_depth = fast.get('bid_depth_1pct', 1)
        
        liquidity_adjusted_pressure = sell_notional / bid_depth if bid_depth > 0 else 0
        
        return {
            'miner_exchange_flow_usd_day': miner_exchange_flow,
            'realization_ratio': realization_ratio,
            'liquidity_adjusted_pressure': liquidity_adjusted_pressure,
        }
    
    def calculate_market_pressure(self):
        """Calculate market pressure from OFI."""
        fast = self.state['fast']
        
        ofi_1m = fast.get('ofi_1', 0)
        ofi_1h = fast.get('ofi_5', 0)  # Use 5-level as proxy
        
        spread = fast.get('spread_bps', 0)
        imbalance = fast.get('imbalance', 0)
        
        # Market pressure = signed OFI / depth
        bid_depth = fast.get('bid_volume', 1)
        
        market_pressure = ofi_1m / bid_depth if bid_depth > 0 else 0
        
        return {
            'ofi_1m': ofi_1m,
            'ofi_1h': ofi_1h,
            'spread_bps': spread,
            'imbalance': imbalance,
            'market_pressure': market_pressure,
        }
    
    def calculate_absorption_pressure(self):
        """Calculate absorption pressure."""
        fast = self.state['fast']
        slow = self.state['slow']
        
        # Aggressive sells
        aggressive_sell = fast.get('sell_volume', 0)
        
        # Incoming buys
        aggressive_buy = fast.get('buy_volume', 0)
        bid_change = fast.get('new_bid_volume', 0) - fast.get('cancelled_bid_volume', 0)
        
        # Buy absorption
        buy_absorption = aggressive_buy + bid_change
        
        # Sell pressure
        miner_sell = slow.get('miner_exchange_flow_usd_day', 0) / 24
        total_sell = miner_sell + aggressive_sell
        
        # Absorption ratio
        absorption_ratio = buy_absorption / total_sell if total_sell > 0 else 1
        
        return {
            'aggressive_buy_usd': aggressive_buy,
            'aggressive_sell_usd': aggressive_sell,
            'bid_change': bid_change,
            'miner_sell_hourly': miner_sell,
            'total_sell_hourly': total_sell,
            'buy_absorption': buy_absorption,
            'absorption_ratio': absorption_ratio,
        }
    
    def calculate_required_buy_flow(self):
        """Calculate required buy flow for zero return."""
        fast = self.state['fast']
        slow = self.state['slow']
        
        # Current pressures
        miner_sell = slow.get('miner_exchange_flow_usd_day', 0) / 24
        aggressive_sell = fast.get('sell_volume', 0)
        bid_cancellations = fast.get('cancelled_bid_volume', 0)
        new_bids = fast.get('new_bid_volume', 0)
        
        # Required buy flow = sell pressure - bid additions + cancellations
        required_buy = miner_sell + aggressive_sell + bid_cancellations - new_bids
        
        return {
            'required_buy_flow_hourly': max(0, required_buy),
            'miner_sell': miner_sell,
            'aggressive_sell': aggressive_sell,
            'bid_cancellations': bid_cancellations,
            'new_bids': new_bids,
        }
    
    def calculate_pressure_balance(self):
        """Calculate the full pressure balance."""
        creation = self.calculate_creation_pressure()
        realization = self.calculate_realization_pressure()
        market = self.calculate_market_pressure()
        absorption = self.calculate_absorption_pressure()
        required = self.calculate_required_buy_flow()
        
        # Overall pressure balance
        total_sell = realization.get('miner_exchange_flow_usd_day', 0) + absorption.get('aggressive_sell_usd', 0)
        total_buy = absorption.get('buy_absorption', 0)
        
        pressure_balance = total_buy / total_sell if total_sell > 0 else 1
        
        fast = self.state['fast']
        
        result = {
            'symbol': self.symbol,
            'timestamp': datetime.now().isoformat(),
            
            # Creation
            'creation_pressure': creation['creation_pressure'],
            'emission_usd_day': creation['emission_usd_day'],
            
            # Realization
            'miner_realization_ratio': realization['realization_ratio'],
            'liquidity_adjusted_pressure': realization['liquidity_adjusted_pressure'],
            
            # Market
            'ofi_1m': market['ofi_1m'],
            'ofi_5l': market['ofi_1h'],
            'spread_bps': market['spread_bps'],
            'imbalance': market['imbalance'],
            
            # Absorption
            'absorption_ratio': absorption['absorption_ratio'],
            'aggressive_buy_usd': absorption['aggressive_buy_usd'],
            'aggressive_sell_usd': absorption['aggressive_sell_usd'],
            
            # Required
            'required_buy_flow_zero_return': required['required_buy_flow_hourly'],
            
            # Overall
            'pressure_balance': pressure_balance,
            
            # Book
            'bid_depth_1pct': fast.get('bid_depth_1pct', 0),
            'bid_depth_5pct': fast.get('bid_depth_5pct', 0),
            'ask_depth_1pct': fast.get('ask_depth_1pct', 0),
            'ask_depth_5pct': fast.get('ask_depth_5pct', 0),
        }
        
        self.history.append(result)
        
        return result
    
    def get_pressure_summary(self):
        """Get human-readable pressure summary."""
        if not self.history:
            return "No data available"
        
        latest = self.history[-1]
        
        summary = f"""
{self.symbol} Pressure Summary
{'='*50}
Creation Pressure:     {latest['creation_pressure']:.2f}
Realization Ratio:     {latest['miner_realization_ratio']:.2%}
Absorption Ratio:      {latest['absorption_ratio']:.2f}
Pressure Balance:      {latest['pressure_balance']:.2f}
Required Buy Flow:     ${latest['required_buy_flow_zero_return']:,.0f}/hour
OFI (1m):              {latest['ofi_1m']:.4f}
Spread:                {latest['spread_bps']:.1f} bps
Book Imbalance:        {latest['imbalance']:.2%}
Bid Depth (1%):        ${latest['bid_depth_1pct']:,.0f}
Bid Depth (5%):        ${latest['bid_depth_5pct']:,.0f}
"""
        return summary

if __name__ == '__main__':
    # Test pressure equation
    print("Testing Pressure Equation...")
    
    # Create pressure calculator for PRL
    pressure = PressureEquation('PRL')
    
    # Set slow state
    pressure.update_slow_state({
        'emission_usd_day': 233284,  # XMR for test
        'miner_exchange_flow_usd_day': 163299,
    })
    
    # Simulate fast state updates
    bids = [["100", "10"], ["99", "20"], ["98", "30"]]
    asks = [["101", "10"], ["102", "20"], ["103", "30"]]
    
    pressure.update_fast_state(bids, asks, timestamp=datetime.now())
    
    # Calculate pressure balance
    result = pressure.calculate_pressure_balance()
    
    print(pressure.get_pressure_summary())
    
    print("\nRaw result:")
    for k, v in result.items():
        print(f"  {k}: {v}")
