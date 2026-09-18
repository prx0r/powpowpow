# PowPowPow API Documentation

## Base URL

```
https://api.powpowpow.dev/v1
```

## Authentication

API key required for write endpoints. Read endpoints are public.

```
Authorization: Bearer <api_key>
```

## Response Format

All responses are JSON with consistent envelope:

```json
{
  "status": "ok",
  "data": {...},
  "meta": {
    "timestamp": "2026-09-18T23:00:00Z",
    "chain": "PRL",
    "source": "prlscan-api"
  }
}
```

---

## Endpoints

### Chains

#### GET /chains
List all tracked chains.

```json
{
  "status": "ok",
  "data": [
    {
      "symbol": "PRL",
      "name": "Pearl",
      "category": "useful-work",
      "physical_resource": "H100 GPU",
      "price_usd": 0.0227,
      "market_cap": 271011
    }
  ]
}
```

#### GET /chains/{symbol}
Get chain details.

#### GET /chains/{symbol}/snapshot
Get latest chain state.

```json
{
  "status": "ok",
  "data": {
    "timestamp": "2026-09-18T23:00:00Z",
    "chain": "PRL",
    "height": 100855,
    "difficulty": 19990000,
    "hashrate": 21900000000000000000,
    "block_reward": 2420.53,
    "tx_count_24h": 2540
  }
}
```

---

### Hardware

#### GET /hardware
List all tracked hardware benchmarks.

```json
{
  "status": "ok",
  "data": [
    {
      "chain": "PRL",
      "hardware_model": "H100",
      "hashrate": 3000000000000000,
      "power_watts": 700,
      "cost_usd": 30000,
      "revenue_usd_day": 0.59,
      "net_profit_usd_day": -28.49
    }
  ]
}
```

#### GET /hardware/{chain}
Get hardware benchmarks for a specific chain.

#### GET /hardware/{chain}/{model}
Get benchmark for specific hardware on a chain.

---

### Live Cards

#### GET /cards
Get all live profitability cards.

```json
{
  "status": "ok",
  "data": {
    "PRL": {
      "coin": "PRL",
      "price_usd": 0.0227,
      "hardware": {
        "H100": {
          "hashrate": 3000000000000000,
          "power_watts": 700,
          "revenue_usd_day": 0.59,
          "electricity_usd_day": 1.68,
          "net_profit_usd_day": -28.49,
          "payback_days": null
        }
      }
    }
  }
}
```

#### GET /cards/{symbol}
Get live card for a specific chain.

---

### Compute Markets

#### GET /compute/markets
Get GPU rental prices across Akash, Clore, Nosana.

```json
{
  "status": "ok",
  "data": {
    "akash": {
      "providers": 150,
      "gpu_models": {"H100": 12, "A100": 45}
    },
    "clore": {
      "servers": 200,
      "gpu_prices": {"RTX_4090": 0.50, "H100": 2.50}
    },
    "nosana": {
      "markets": 50
    }
  }
}
```

#### GET /compute/benchmarks
Get normalized compute benchmarks.

```json
{
  "status": "ok",
  "data": {
    "timestamp": "2026-09-18T23:00:00Z",
    "gpu_classes": {
      "h100_plus": {"median_usd_hour": 2.50, "available_units": 50},
      "datacenter_a100": {"median_usd_hour": 1.80, "available_units": 100},
      "consumer_high": {"median_usd_hour": 0.50, "available_units": 500}
    }
  }
}
```

---

### Exchanges

#### GET /exchanges
List connected exchanges.

#### GET /exchanges/{exchange}/markets
List markets on an exchange.

#### GET /exchanges/{exchange}/{symbol}/orderbook
Get order book.

```json
{
  "status": "ok",
  "data": {
    "exchange": "safetrade",
    "symbol": "PRL/USDT",
    "bids": [["0.0226", "1000000"]],
    "asks": [["0.0228", "500000"]],
    "spread_bps": 88.5,
    "mid": 0.0227
  }
}
```

#### GET /exchanges/{exchange}/{symbol}/trades
Get recent trades.

---

### Metrics

#### GET /metrics/pressure/{symbol}
Get pressure equation metrics.

```json
{
  "status": "ok",
  "data": {
    "chain": "PRL",
    "creation_pressure": 3888.07,
    "miner_realization_ratio": 0.70,
    "absorption_ratio": 0.01,
    "pressure_balance": 0.00,
    "required_buy_flow_hourly": 6744
  }
}
```

#### GET /metrics/resource-premium
Get resource premium across all chains.

```json
{
  "status": "ok",
  "data": [
    {
      "chain": "PRL",
      "mining_revenue_per_gpu_hour": 0.025,
      "external_rental_per_gpu_hour": 2.50,
      "resource_premium": 0.01
    }
  ]
}
```

#### GET /metrics/miner-economics
Get miner economics for all chains.

---

### Factors

#### GET /factors
Get cross-chain factor table.

```json
{
  "status": "ok",
  "data": [
    {
      "chain": "PRL",
      "issuance_usd_24h": 233284,
      "dilution_pressure": 0.0084,
      "absorption_ratio": 663,
      "sell_pressure_usd_24h": 163299
    }
  ]
}
```

---

## WebSocket

Connect to `wss://api.powpowpow.dev/v1/ws` for real-time data.

### Subscribe

```json
{
  "method": "subscribe",
  "channels": ["chain:PRL", "chain:XMR", "compute:benchmarks"]
}
```

### Messages

```json
{
  "channel": "chain:PRL",
  "data": {
    "timestamp": "2026-09-18T23:00:00Z",
    "price_usd": 0.0227,
    "hashrate": 21900000000000000000
  }
}
```

---

## Rate Limits

| Tier | Requests/min | WebSocket connections |
|------|--------------|----------------------|
| Free | 60 | 1 |
| Pro | 600 | 10 |
| Enterprise | 6000 | 100 |

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 429 | Rate limited |
| 500 | Server error |
