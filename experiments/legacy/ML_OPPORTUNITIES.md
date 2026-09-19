# PowPowPow — What ML Can We Do?

## Data We Have Now

| Data Type | Status | Volume |
|-----------|--------|--------|
| L2 Order Book | ✅ Live | 6000+ snapshots across 10 coins |
| OHLCV Daily | ✅ Historical | 500 days (QUBIC, XEL), 178 (PRL), 145 (NOCK) |
| Trades | ✅ Live | Real-time via WebSocket |
| Feature Vectors | ✅ Generated | 22 features per coin |

---

## ML Models We Can Build

### 1. Price Direction (Classification)
**Target:** Will price go up or down in next 1h/4h/24h?
**Features:** Technical indicators + order book imbalance
**Status:** Baseline trained (43-61% accuracy)

### 2. Volatility Forecasting (Regression)
**Target:** Next period's volatility
**Features:** Historical volatility, ATR, Bollinger width
**Use:** Position sizing, risk management

### 3. Order Book Imbalance Signal
**Target:** Price move within 5-15 minutes
**Features:** Bid/ask ratio, depth at levels, spread
**Status:** Features ready, need more L2 data

### 4. Spread Prediction
**Target:** Future spread width
**Features:** Current spread, volume, time of day
**Use:** Market making, execution timing

### 5. Trade Flow Toxicity (VPIN)
**Target:** Informed trading probability
**Features:** Trade size distribution, buy/sell imbalance
**Use:** Detect smart money

### 6. Cross-Asset Signals
**Target:** Correlated moves across coins
**Features:** All coins simultaneously
**Use:** Pairs trading, hedging

### 7. Anomaly Detection
**Target:** Unusual activity
**Features:** All features deviating from normal
**Use:** Alert system

---

## Priority Order

1. **Accumulate L2 data** (30-90 days)
2. **Build order book features** (imbalance, depth, spread)
3. **Train L2-enhanced models** (should beat OHLCV-only)
4. **Backtest strategies** (paper trading)
5. **Deploy live predictions** (dashboard)

---

## What's Missing for Better ML

- More L2 history (running collector)
- Chain metrics (emission, hashrate)
- Miner wallet tracking
- Sentiment data
- Cross-exchange data
