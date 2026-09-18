"""
Two-Timescale Model
Separates structural pressure from microstructure triggers.
"""

import json
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/home/box/powpowpow')
from pressure import PressureEquation

class TwoTimescaleModel:
    """
    Predicts returns using:
    - Slow state: structural pressure (hours/days)
    - Fast state: microstructure triggers (ms/minutes)
    """
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.pressure = PressureEquation(symbol)
        self.slow_history = []
        self.fast_history = []
        self.returns = []
    
    def update_slow_state(self, data):
        """Update slow-moving structural variables."""
        self.pressure.update_slow_state(data)
        
        slow_snapshot = {
            'timestamp': datetime.now().isoformat(),
            **self.pressure.state['slow'],
        }
        self.slow_history.append(slow_snapshot)
    
    def update_fast_state(self, bids, asks, trades=None):
        """Update fast-moving microstructure variables."""
        fast = self.pressure.update_fast_state(bids, asks, trades)
        
        fast_snapshot = {
            'timestamp': datetime.now().isoformat(),
            **fast,
        }
        self.fast_history.append(fast_snapshot)
    
    def record_return(self, return_pct):
        """Record actual return for training."""
        self.returns.append({
            'timestamp': datetime.now().isoformat(),
            'return_pct': return_pct,
        })
    
    def get_features(self):
        """Get combined feature vector for prediction."""
        if not self.slow_history or not self.fast_history:
            return None
        
        slow = self.slow_history[-1]
        fast = self.fast_history[-1]
        
        features = {
            # Slow state (structural)
            'emission_usd_day': slow.get('emission_usd_day', 0),
            'miner_exchange_flow': slow.get('miner_exchange_flow_usd_day', 0),
            'hashrate': slow.get('hashrate', 0),
            'difficulty': slow.get('difficulty', 0),
            'circulating_supply': slow.get('circulating_supply', 0),
            'market_cap': slow.get('market_cap', 0),
            
            # Fast state (trigger)
            'ofi_1': fast.get('ofi_1', 0),
            'ofi_5': fast.get('ofi_5', 0),
            'ofi_10': fast.get('ofi_10', 0),
            'spread_bps': fast.get('spread_bps', 0),
            'imbalance': fast.get('imbalance', 0),
            'microprice': fast.get('microprice', 0),
            'bid_depth_1pct': fast.get('bid_depth_1pct', 0),
            'ask_depth_1pct': fast.get('ask_depth_1pct', 0),
            'bid_depth_5pct': fast.get('bid_depth_5pct', 0),
            'ask_depth_5pct': fast.get('ask_depth_5pct', 0),
            
            # Pressure metrics
            'creation_pressure': self.pressure.calculate_creation_pressure()['creation_pressure'],
            'realization_ratio': self.pressure.calculate_realization_pressure()['realization_ratio'],
            'absorption_ratio': self.pressure.calculate_absorption_pressure()['absorption_ratio'],
            'pressure_balance': self.pressure.calculate_pressure_balance()['pressure_balance'],
        }
        
        return features
    
    def predict_pressure_regime(self):
        """Predict market regime from pressure state."""
        features = self.get_features()
        if not features:
            return {'regime': 'unknown', 'confidence': 0}
        
        # Simple heuristic rules (will be replaced by ML)
        score = 0
        
        # Structural pressure
        if features['creation_pressure'] > 1:
            score -= 2  # High creation pressure
        elif features['creation_pressure'] > 0.5:
            score -= 1
        
        if features['realization_ratio'] > 0.7:
            score -= 2  # Miners selling a lot
        elif features['realization_ratio'] > 0.4:
            score -= 1
        
        if features['absorption_ratio'] > 1.5:
            score += 2  # Strong buying
        elif features['absorption_ratio'] > 1:
            score += 1
        
        # Microstructure
        if features['ofi_1'] > 0.1:
            score += 1
        elif features['ofi_1'] < -0.1:
            score -= 1
        
        if features['imbalance'] > 0.2:
            score += 1
        elif features['imbalance'] < -0.2:
            score -= 1
        
        if features['spread_bps'] < 10:
            score += 0.5  # Tight spread = healthy
        elif features['spread_bps'] > 50:
            score -= 0.5  # Wide spread = stressed
        
        # Determine regime
        if score >= 2:
            regime = 'accumulation'
            confidence = min(0.8, 0.5 + score * 0.1)
        elif score <= -2:
            regime = 'distribution'
            confidence = min(0.8, 0.5 + abs(score) * 0.1)
        else:
            regime = 'neutral'
            confidence = 0.5
        
        return {
            'regime': regime,
            'score': score,
            'confidence': confidence,
            'factors': {
                'creation_pressure': features['creation_pressure'],
                'realization_ratio': features['realization_ratio'],
                'absorption_ratio': features['absorption_ratio'],
                'ofi': features['ofi_1'],
                'imbalance': features['imbalance'],
            }
        }
    
    def get_pressure_report(self):
        """Generate full pressure report."""
        features = self.get_features()
        prediction = self.predict_pressure_regime()
        
        if not features:
            return "No data available"
        
        report = f"""
{'='*60}
{self.symbol} Two-Timescale Pressure Report
{'='*60}

STRUCTURAL STATE (Slow)
{'-'*40}
Emission/day:        ${features['emission_usd_day']:,.0f}
Miner sell flow:     ${features['miner_exchange_flow']:,.0f}
Creation Pressure:   {features['creation_pressure']:.2f}
Realization Ratio:   {features['realization_ratio']:.2%}
Hashrate:            {features.get('hashrate', 'N/A')}
Market Cap:          ${features['market_cap']:,.0f}

MICROSTRUCTURE (Fast)
{'-'*40}
OFI (1-level):       {features['ofi_1']:.4f}
OFI (5-level):       {features['ofi_5']:.4f}
Spread:              {features['spread_bps']:.1f} bps
Imbalance:           {features['imbalance']:.2%}
Microprice:          ${features['microprice']:.8f}

DEPTH
{'-'*40}
Bid Depth (1%):      ${features['bid_depth_1pct']:,.0f}
Ask Depth (1%):      ${features['ask_depth_1pct']:,.0f}
Bid Depth (5%):      ${features['bid_depth_5pct']:,.0f}
Ask Depth (5%):      ${features['ask_depth_5pct']:,.0f}

PRESSURE BALANCE
{'-'*40}
Absorption Ratio:    {features['absorption_ratio']:.2f}
Pressure Balance:    {features['pressure_balance']:.2f}

REGIME PREDICTION
{'-'*40}
Regime:              {prediction['regime'].upper()}
Score:               {prediction['score']:.1f}
Confidence:          {prediction['confidence']:.0%}

INTERPRETATION
{'-'*40}
"""
        if prediction['regime'] == 'distribution':
            report += "Structural selling pressure dominates. Miners are realizing gains.\n"
            report += f"Required buy flow to maintain price: need ${features.get('required_buy_flow_zero_return', 0):,.0f}/hour of fresh demand.\n"
        elif prediction['regime'] == 'accumulation':
            report += "Strong buying absorption. Market is absorbing sell pressure.\n"
            report += "Pressure is being absorbed by willing buyers.\n"
        else:
            report += "Balanced pressure. No clear directional bias.\n"
        
        return report

if __name__ == '__main__':
    # Test two-timescale model
    print("Testing Two-Timescale Model...")
    
    model = TwoTimescaleModel('PRL')
    
    # Set slow state
    model.update_slow_state({
        'emission_usd_day': 233284,
        'miner_exchange_flow_usd_day': 163299,
        'hashrate': 5.6e9,
        'difficulty': 691e9,
        'circulating_supply': 18446744,
        'market_cap': 8.5e9,
    })
    
    # Update fast state
    bids = [["100", "10"], ["99", "20"], ["98", "30"]]
    asks = [["101", "10"], ["102", "20"], ["103", "30"]]
    model.update_fast_state(bids, asks)
    
    # Get report
    print(model.get_pressure_report())
