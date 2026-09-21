# PowPowPow — Unsure / Open Questions

## Resolved 2026-09-19 (shipped)

- **Q2 raw vs snapshots:** BOTH. Raw stays immutable (WS ticks batched
  200 frames/5s after measuring ~1k files/min naive); normalized JSONL
  is the hot query layer; nightly Parquet compact measured **16.8x**
  (`scripts/compact_parquet.py`, DuckDB-verified).
- **Q8 database:** Parquet + DuckDB, no server (`pip install pyarrow
  duckdb`). QuestDB/Timescale/ClickHouse deferred until SQL/Grafana
  needs earn the ops cost.
- **Q9 WS reconnects:** exponential backoff + resubscribe in
  `venue_l2` REST (checkpoints) and `venue_ws` + `l2_archival` (tick),
  all systemd-supervised with restart.
- **Q10 retention:** keep everything; Parquet makes it ~1/17th the bytes.
- **Q11 PowDaily:** seed exists as compiled coin pages
  (`scripts/compile_coins.py` → `pages/`); video pipeline not started.
- **Q4/Q5 electricity/depreciation:** inputs, not constants
  (`electricity_usd_kwh` param, 3yr straight-line default, assumptions
  printed on every card).

## Schema Questions (original, kept for history)

### 1. How to handle rate limiting across 8 chains?
Some APIs (CoinGecko, Binance) have strict rate limits. Need a proper rate limiter or queue system.

**Options:**
- Token bucket per API
- Rotating API keys
- Caching layer with TTL
- Priority queue (V1 chains first)

**Decision needed:** Implement before scaling collectors.

### 2. Point-in-time backtesting
Should we store EVERY raw event, or just normalized snapshots?

**Tradeoff:**
- Every raw event = massive storage but perfect reconstruction
- Snapshots only = smaller but loses some granularity

**Current approach:** Store all raw events. May need to revisit.

### 3. Hardware benchmark source of truth
Where do we get authoritative hardware benchmarks?

**Options:**
- Manufacturer specs (theoretical)
- Pool-reported hashrates (practical)
- Our own benchmarks (best but requires hardware)
- Community benchmarks (variable quality)

**Current approach:** Use published pool benchmarks + manufacturer specs.

### 4. Electricity cost estimation
How do we estimate electricity cost for each chain?

**Options:**
- Fixed global average ($0.10/kWh)
- Regional averages (US, EU, Asia)
- Miner-reported costs (not available)
- Hardware TDP × electricity price

**Current approach:** Fixed $0.10/kWh default, override per chain if known.

### 5. Hardware depreciation model
How to model GPU/ASIC depreciation?

**Options:**
- Straight-line over 3 years
- Accelerated depreciation (50% year 1)
- Market resale value curve
- Difficulty-adjusted useful life

**Current approach:** Straight-line over 3 years.

## Data Quality Questions

### 6. How to detect stale/incorrect data?
Some APIs may return outdated data. How do we validate freshness?

**Options:**
- Timestamp comparison (data age)
- Cross-reference multiple sources
- Anomaly detection (sudden jumps)
- Manual validation

**Current approach:** Timestamp + basic anomaly checks.

### 7. How to handle API changes/breaks?
When an API changes format or goes down, how do we handle it gracefully?

**Options:**
- Schema versioning
- Fallback sources
- Alert system
- Graceful degradation

**Current approach:** Log errors, continue with available data.

## Architecture Questions

### 8. Should we use a database instead of JSON files?
JSON files are simple but don't scale well for queries.

**Options:**
- SQLite (simple, no setup)
- DuckDB (analytical queries)
- PostgreSQL (production)
- Keep JSON (current)

**Current approach:** JSON files. May need to migrate for analytics.

### 9. How to handle WebSocket reconnections?
WebSocket connections drop. How to handle reconnection gracefully?

**Options:**
- Auto-reconnect with exponential backoff
- Health check + manual restart
- Daemon process with supervisor

**Current approach:** Auto-reconnect in collector.

### 10. What's the retention policy?
How long do we keep raw data?

**Options:**
- Forever (moat)
- Compress after 30 days
- Archive to cold storage after 1 year
- Keep only normalized data after 90 days

**Current approach:** Keep everything (moat strategy).

## Product Questions

### 11. How to generate PowDaily automatically?
Need a report generator that produces daily summary.

**Options:**
- Python script → Markdown → Video
- Python script → JSON → API
- Python script → HTML → Screenshot

**Current approach:** Not yet implemented.

### 12. How to expose the API publicly?
Need authentication, rate limiting, documentation.

**Options:**
- API key system
- Public read, private write
- Tiered access

**Current approach:** Local API only.

## Business Questions

### 13. Is this a data product or a content product?
The moat is the data, but revenue may come from content/API.

**Options:**
- Sell data feeds
- Sell API access
- Sell content/analysis
- All of the above

**Current approach:** Build data first, decide later.

### 14. How to compete with Glassnode/CryptoQuant?
They have more resources but focus on BTC/ETH.

**Differentiation:**
- Focus on niche chains (PRL, QUBIC, etc.)
- Hardware-level telemetry (they don't do this)
- Real-time supplier economics
- Cross-chain resource comparison

**Current approach:** Niche focus + hardware telemetry.

### 15. What's the minimum viable product?
What do we need to launch?

**Options:**
- API with 3 chains
- Daily report for 1 chain
- Dashboard with all 8 chains
- just the data pipeline

**Current approach:** Data pipeline first, product later.
