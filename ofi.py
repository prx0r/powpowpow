"""
OFI — Order Flow Imbalance Calculator
Multi-level OFI from L2 data.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

class OFICalculator:
    """Calculate Order Flow Imbalance from L2 depth updates."""
    
    def __init__(self):
        self.order_book = {'bids': {}, 'asks': {}}
        self.history = []
        self.trade_history = []
    
    def update_depth(self, bids, asks, timestamp=None):
        """Update order book from depth snapshot."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Store previous state for delta calculation
        prev_bids = dict(self.order_book['bids'])
        prev_asks = dict(self.order_book['asks'])
        
        # Update book
        self.order_book['bids'] = {str(b[0]): float(b[1]) for b in bids}
        self.order_book['asks'] = {str(a[0]): float(a[1]) for a in asks}
        
        # Record history
        self.history.append({
            'timestamp': timestamp,
            'bids': dict(self.order_book['bids']),
            'asks': dict(self.order_book['asks']),
        })
        
        return self.calculate_ofi(prev_bids, prev_asks)
    
    def calculate_ofi(self, prev_bids, prev_asks):
        """Calculate OFI from book changes."""
        # New bids (in book now but not before)
        new_bid_volume = sum(
            self.order_book['bids'].get(p, 0) 
            for p in self.order_book['bids'] 
            if p not in prev_bids
        )
        
        # Cancelled bids (was in book but not anymore)
        cancelled_bid_volume = sum(
            prev_bids.get(p, 0) 
            for p in prev_bids 
            if p not in self.order_book['bids']
        )
        
        # New asks
        new_ask_volume = sum(
            self.order_book['asks'].get(p, 0)
            for p in self.order_book['asks']
            if p not in prev_asks
        )
        
        # Cancelled asks
        cancelled_ask_volume = sum(
            prev_asks.get(p, 0)
            for p in prev_asks
            if p not in self.order_book['asks']
        )
        
        # OFI = (new bids - cancelled bids) - (new asks - cancelled asks)
        ofi = (new_bid_volume - cancelled_bid_volume) - (new_ask_volume - cancelled_ask_volume)
        
        return {
            'ofi': ofi,
            'new_bid_volume': new_bid_volume,
            'cancelled_bid_volume': cancelled_bid_volume,
            'new_ask_volume': new_ask_volume,
            'cancelled_ask_volume': cancelled_ask_volume,
        }
    
    def calculate_multi_level_ofi(self, levels=[1, 5, 10, 25]):
        """Calculate OFI at multiple book levels."""
        if not self.history or len(self.history) < 2:
            return {}
        
        current = self.history[-1]
        prev = self.history[-2]
        
        result = {}
        for n in levels:
            # Top N bids
            top_bids = sorted(current['bids'].items(), key=lambda x: float(x[0]), reverse=True)[:n]
            prev_top_bids = sorted(prev['bids'].items(), key=lambda x: float(x[0]), reverse=True)[:n]
            
            top_asks = sorted(current['asks'].items(), key=lambda x: float(x[0]))[:n]
            prev_top_asks = sorted(prev['asks'].items(), key=lambda x: float(x[0]))[:n]
            
            bid_volume = sum(float(b[1]) for b in top_bids)
            prev_bid_volume = sum(float(b[1]) for b in prev_top_bids)
            
            ask_volume = sum(float(a[1]) for a in top_asks)
            prev_ask_volume = sum(float(a[1]) for a in prev_top_asks)
            
            ofi = (bid_volume - prev_bid_volume) - (ask_volume - prev_ask_volume)
            result[f'ofi_{n}'] = ofi
        
        return result
    
    def calculate_book_metrics(self):
        """Calculate book-level metrics."""
        if not self.order_book['bids'] or not self.order_book['asks']:
            return {}
        
        bids = self.order_book['bids']
        asks = self.order_book['asks']
        
        bid_prices = sorted([float(p) for p in bids.keys()])
        ask_prices = sorted([float(p) for p in asks.keys()])
        
        if not bid_prices or not ask_prices:
            return {}
        
        best_bid = max(bid_prices)
        best_ask = min(ask_prices)
        mid = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        spread_bps = (spread / mid) * 10000 if mid > 0 else 0
        
        bid_volume = sum(bids.values())
        ask_volume = sum(asks.values())
        total_volume = bid_volume + ask_volume
        
        # Depth at percentages
        def depth_at_pct(ref_price, book, pct, side='bid'):
            if side == 'bid':
                threshold = ref_price * (1 - pct/100)
                return sum(v for k, v in book.items() if float(k) >= threshold)
            else:
                threshold = ref_price * (1 + pct/100)
                return sum(v for k, v in book.items() if float(k) <= threshold)
        
        # Book imbalance
        imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
        
        # Microprice (volume-weighted mid)
        if bid_volume + ask_volume > 0:
            microprice = (best_bid * ask_volume + best_ask * bid_volume) / (bid_volume + ask_volume)
        else:
            microprice = mid
        
        return {
            'best_bid': best_bid,
            'best_ask': best_ask,
            'mid': mid,
            'spread': spread,
            'spread_bps': spread_bps,
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'imbalance': imbalance,
            'microprice': microprice,
            'bid_depth_1pct': depth_at_pct(mid, bids, 1, 'bid'),
            'ask_depth_1pct': depth_at_pct(mid, asks, 1, 'ask'),
            'bid_depth_5pct': depth_at_pct(mid, bids, 5, 'bid'),
            'ask_depth_5pct': depth_at_pct(mid, asks, 5, 'ask'),
            'bid_depth_10pct': depth_at_pct(mid, bids, 10, 'bid'),
            'ask_depth_10pct': depth_at_pct(mid, asks, 10, 'ask'),
            'num_bid_levels': len(bids),
            'num_ask_levels': len(asks),
        }
    
    def record_trade(self, price, amount, side, timestamp=None):
        """Record a trade for trade-based OFI."""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.trade_history.append({
            'timestamp': timestamp,
            'price': float(price),
            'amount': float(amount),
            'side': side,
            'notional': float(price) * float(amount),
        })
    
    def calculate_trade_ofi(self, window_seconds=60):
        """Calculate OFI from trades in recent window."""
        if not self.trade_history:
            return {}
        
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        recent_trades = [t for t in self.trade_history if t['timestamp'] >= cutoff]
        
        if not recent_trades:
            return {}
        
        buy_volume = sum(t['notional'] for t in recent_trades if t['side'] == 'buy')
        sell_volume = sum(t['notional'] for t in recent_trades if t['side'] == 'sell')
        total = buy_volume + sell_volume
        
        trade_ofi = (buy_volume - sell_volume) / total if total > 0 else 0
        
        return {
            'trade_ofi': trade_ofi,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'trade_count': len(recent_trades),
            'avg_trade_size': total / len(recent_trades) if recent_trades else 0,
        }

if __name__ == '__main__':
    # Test OFI calculator
    calc = OFICalculator()
    
    # Simulate some depth updates
    print("Testing OFI Calculator...")
    
    # Initial book
    bids = [["100", "10"], ["99", "20"], ["98", "30"]]
    asks = [["101", "10"], ["102", "20"], ["103", "30"]]
    
    result = calc.update_depth(bids, asks)
    print(f"Initial OFI: {result['ofi']}")
    
    # Add some bids
    bids = [["100", "15"], ["99", "25"], ["98", "30"], ["97", "50"]]
    asks = [["101", "10"], ["102", "20"], ["103", "30"]]
    
    result = calc.update_depth(bids, asks)
    print(f"After adding bids: OFI = {result['ofi']}")
    print(f"  New bid volume: {result['new_bid_volume']}")
    print(f"  Cancelled bid volume: {result['cancelled_bid_volume']}")
    
    # Get book metrics
    metrics = calc.calculate_book_metrics()
    print(f"\nBook Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
