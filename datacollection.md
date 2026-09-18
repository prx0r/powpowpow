# PowPowPow Data Collection & Moat Specification

## Global Inputs: Simple, Durable, Consistent

For global GPU/electricity inputs, **don't chase perfect minute-level truth**. Pick durable benchmark series with stable definitions, snapshot them consistently, and preserve raw observations. The moat is continuity.

### Compute Benchmarks (Three Layers)

1. **Akash available GPU capacity** — "decentralized compute supply" proxy
2. **Clore spot/on-demand GPU prices** — real decentralized rental-price proxy
3. **Nosana market price/availability** — second independent GPU-market benchmark

Normalize to durable series:
```text
compute_benchmark_hourly
  hour
  gpu_class              # consumer_high, datacenter_a100, h100_plus
  median_rental_usd_hour
  p25_rental_usd_hour
  p75_rental_usd_hour
  available_units
  active_units
  source_count
```

Create **stable GPU classes** and retain raw source rows.

### Electricity Benchmarks

```text
energy_benchmark_daily
  date
  region
  benchmark_type         # wholesale, industrial retail
  usd_kwh
  source
```

Never mix observed grid price with estimated miner electricity cost.

## Data Pipeline Architecture

```
collector → raw immutable blob → validator → normalized row → hourly/daily aggregates → derived factors
```

Every collector stores:
- `source_url`
- `source_timestamp`
- `received_at`
- `schema_version`
- `raw_payload_hash`
- `raw_payload`

If an API dies in 2019, historical series remains intact.

## Exchange Venues

### Primary: SafeTrade
Weird frontier assets, L2 data.

### Secondary: Gate
- Spot L2 at 100ms with sequence IDs
- REST snapshots + incremental WebSocket updates
- Futures L2 available

```text
REST: https://api.gateio.ws/api/v4/spot/order_book
WS:   wss://api.gateio.ws/ws/v4/
Channels: spot.order_book_update, spot.book_ticker, spot.trades
```

### Tertiary: CoinEx
- v2 WebSocket, 50 levels, ~200ms push
- Incremental/full updates, CRC32 checksums
- Good for mineable/smaller assets

```text
REST: https://api.coinex.com/v2
WS:   wss://socket.coinex.com/v2/spot
```

### Venue Discovery (Automated)

```text
asset = PRL
venues:
  safetrade PRL/USDT
  gate      ...
  coinex    ...
```

Daily job queries exchanges, maps to canonical assets, auto-starts collectors.

## Granularity Split

| Data Type | Granularity | Rationale |
|-----------|-------------|-----------|
| L2/trades | Raw event | Cannot reconstruct |
| Chain blocks | Raw block/event | Cannot reconstruct |
| Miner/provider telemetry | 1-5 min | Reasonable |
| GPU rental benchmarks | Hourly | Plenty |
| GPU hardware prices | Daily | Plenty |
| Electricity | Hourly/daily | As available |
| Protocol/GitHub | Event + daily snapshot | Enough |

## Stable External Indices

Publish own indices:
```text
PPP_GPU_RENT_H100
PPP_GPU_RENT_CONSUMER
PPP_GPU_CAPACITY_H100
PPP_ELECTRICITY_US
PPP_ELECTRICITY_EU
PPP_KAS_ASIC_CAPEX
```

Example:
```
PPP_GPU_RENT_H100 = median(Akash H100, Clore H100, Nosana H100)
```

If source disappears, index continues with remaining constituents.

## Miner Comparison Framework

```text
PRL:  PRL_H100_REVENUE_HOUR / PPP_GPU_RENT_H100
QUBIC: QUBIC_COMPUTE_REVENUE_HOUR / PPP_COMPUTE_OPPORTUNITY_COST
KAS:  KAS_ASIC_REVENUE_DAY - PPP_ELECTRICITY_REGION * kWh
```

**Sources are replaceable. Metrics and historical methodology are permanent.**

## V1 Collection Matrix

| Feed | Granularity | Historical Backfill | Start Live |
|------|-------------|---------------------|------------|
| SafeTrade L2 | event | limited | YES |
| SafeTrade trades | event | likely | YES |
| Gate L2 | event | no | YES |
| Gate trades | event | no | YES |
| CoinEx L2 | event | no | YES |
| PRL blocks/mining | block | yes | YES |
| PRL entity flows | tx | yes | YES |
| QUBIC ticks | ~1 sec | partly | YES |
| QUBIC epochs/computors | epoch/tick | yes | YES |
| QUAN node/miner | seconds | limited | YES |
| XMR blocks/difficulty | block | yes | yes |
| KAS DAA/blocks | event | yes | yes |
| Akash providers | 1-5 min | incomplete | YES |
| Clore marketplace | 1-5 min | unlikely | YES |
| Nosana markets/hosts | 1-5 min | incomplete | YES |
| electricity | 5m-monthly | mostly yes | yes |
| GPU prices | hourly/daily | poor | YES |
| mining software | release | yes-ish | yes |

Bold = delay destroys future data.
