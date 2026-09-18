# PowPowPow PR1 — Data-Integrity Hardening

> **18 September 2026 becomes Day 0 of a dataset that gets objectively harder to reproduce every day afterward.**

## P0 Issues to Fix

### 1. Bitemporal timestamps
Every observation needs both:
- `event_time` — when the thing happened (from source)
- `observed_at` — when we received it

Never substitute `observed_at` for `event_time`.

### 2. UTC-aware timestamps only
Switch to `datetime.now(timezone.utc)`. Store `Z`/`+00:00` explicitly.

### 3. Append-only raw storage
`clore_data.json`, `nos_data.json`, `akt_data.json` overwrite daily. Must archive every response via `store_raw_event()` before parsing.

### 4. Move raw archival into `fetch_json()`
Every network call automatically records:
```
request_started_at
response_received_at
http_status
headers_subset
request_params
raw_body
parsed_payload
payload_hash
```

### 5. PRL source hierarchy
PearlTrack = derived/enrichment/labels
Your own pearld = canonical_chain

Add:
```
classification_source
classification_version
classification_confidence
```

### 6. Ban generic `timestamp`
Use explicit names:
```
block_time, trade_time, event_time, observed_at, normalized_at
```

### 7. Raw lineage into normalized data
Every normalized row needs:
```
raw_event_id
source_id
normalizer_version
schema_version
```

### 8. Canonical payload hashing
Use deterministic serialization:
```python
json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
```

### 9. L2 archival hardening
- Exchange event timestamp
- WebSocket receive timestamp
- Sequence/update ID
- Snapshot vs delta flag
- Gap detection
- Periodic REST checkpoints
- Raw message before interpretation

### 10. Schema abstraction
Use `network_id` instead of ticker symbols:
```
network_id = "pearl-mainnet"
asset_id = "PRL"
resource_type = "gpu_compute"
```

### 11. MinerEconomics provenance
Store assumptions with references:
```
electricity_benchmark_id
hardware_price_observation_id
amortization_methodology_version
calculation_version
```

### 12. Remove old universe from README
One source of truth: `v1_registry.py` (8 systems)

### 13. Add recoverability field
```
recoverability: irreversible | partial | reconstructable
priority: P0 | P1 | P2
cadence_seconds: ...
```

### 14. Data-quality telemetry
```
collector_run
  observations_received
  observations_written
  source_latency_ms
  gap_detected
  coverage_pct
```

### 15. Don't keep raw history in Git
Design paths as storage abstractions:
```
raw://...
normalized://...
```

## Priority Order

1. Fix timestamps + raw archival + provenance
2. Make SafeTrade L2 gap-safe
3. Make Clore/Akash/Nosana fully append-only
4. PRL first-party chain data
5. Wire QUAN live Prometheus
6. Dashboards, pressure equations, ML

## What's Already Good

- `v1_registry.py` captures scarce resource, supplier, telemetry, cost, reward, supply-response
- `v1_pipeline.py` has correct flow: Source → Raw → Normalized → Live Cards
- `l2_archival.py` recognizes raw market microstructure must be archived
- Eight-core V1 is the right scope

## Target V1

```
PRL, QUBIC, QUAN, XMR, KAS, CLORE, AKT, NOS
```

Day 0 = 18 September 2026.
