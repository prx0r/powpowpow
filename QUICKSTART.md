# PowPowPow — Quick Start

## 1. Start Data Collector

```bash
cd /home/box/safetrade
python3 daemon.py start
```

## 2. Start API

```bash
cd /home/box/powpowpow/api
source /home/box/safetrade/venv/bin/activate
python3 app.py
```

## 3. Open Dashboard

Open `powpowpow/dashboard/index.html` in browser.

## 4. Get Predictions

```bash
cd /home/box/safetrade
python3 live_predictions.py
```

## 5. Collect Chain Metrics

```bash
cd /home/box/powpowpow
python3 scripts/collect_metrics.py
```

## Commands

```bash
# Collector
python3 /home/box/safetrade/daemon.py status
python3 /home/box/safetrade/daemon.py start
python3 /home/box/safetrade/daemon.py stop

# ML Pipeline
python3 /home/box/safetrade/feature_pipeline.py
python3 /home/box/safetrade/train_model.py
python3 /home/box/safetrade/live_predictions.py

# Metrics
python3 /home/box/powpowpow/scripts/collect_metrics.py
```
