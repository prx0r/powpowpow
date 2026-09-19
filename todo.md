# PowPowPow — 20 Moat Foundations Todo

## The Core Insight

PowPowPow should be not just a database, but a **point-in-time research system**.

After four years, PowPowPow should possess:
1. **Reality history** — what physically/economically happened
2. **Knowledge history** — what could have been known at the time
3. **Decision history** — what PowPowPow believed should happen next

Then you can compare Reality_t vs Knowledge_t vs Prediction_t.

---

## The 20 Foundations

### 1. Permanent IDs for everything
Never let ticker, pool name, exchange symbol, GPU SKU text, or wallet label be the primary identifier. Use stable IDs:
- network_id: pearl-mainnet
- asset_id: prl-asset-001
- supplier_id: prl-pool-0007
- hardware_id: nvidia-h100-sxm-80gb
- exchange_market: safetrade-prl-usdt
- source_id: pearltrack-network-v1

Maintain history of names/symbols separately.

### 2. Preserve the universe itself through time
Every day store universe_snapshot with status (eligible/watch/excluded/dead/delisted) and qualification_reason. Prevents survivorship bias.

### 3. Store revisions, not corrected values
Do not replace 8.2 with 7.5. Store both with known_at and superseded_at. Enables economic reality backtest vs tradable-information backtest.

### 4. Cryptographically timestamp the warehouse
Daily manifest with raw object count, normalized rows, source count, Merkle root. Publish/sign independently. Use OpenTimestamps for Bitcoin-backed proofs.

### 5. Public daily checkpoints
Publish date, row count, source count, Merkle root, schema version. Turns historical provenance into a feature.

### 6. Data quality history as part of the dataset
Store source_quality_daily: coverage_pct, largest_gap, median_latency, p95_latency, schema_errors, sequence_gaps, reconnects, confidence_grade.

### 7. Redundant observation of important facts
Collect same quantity from multiple sources, preserve disagreements. Do not collapse into one number. measurement_disagreement is itself informative.

### 8. Archive negative observations
Record: no H100 available, pool endpoint unreachable, miner count zero, no bids at 5% depth, market disappeared. Absence is often the scarcity signal.

### 9. Preserve source semantics
Store source_schema, source_version, source_documentation_hash, parser_version. Track semantic events when APIs change meaning.

### 10. Version every derived equation
Never have resource_premium without metric_version. Inputs must be versioned too. RP_v1 and RP_v2 coexist.

### 11. Freeze every research experiment
Save experiment_id, created_at, hypothesis, code_commit, dataset_root_hash, feature_versions, universe_snapshot, training_window, test_window, cost_model, execution_model, results.

### 12. Create a hypothesis registry
Store hypothesis, created_at, causal_chain, expected_lags, kill_conditions. Never rewrite original hypothesis. Add evaluations.

### 13. Record predictions before outcomes exist
Daily forecast_snapshot: predicted, model_version, confidence. Hash/timestamp it. Outcomes arrive later.

### 14. Record counterfactual decisions every day
For each hardware archetype: best_action, expected, complete ranked opportunity set. Years later answer: what would an agent have done?

### 15. Start active probes from multiple regions
Europe, US, Asia. Measure exchange websocket arrival, RPC response, pool Stratum jobs, marketplace availability, node propagation.

### 16. Hardware benchmark time series
Never write H100 PRL = 203 TH/s as permanent. Make it: hardware, miner software, version, driver, CUDA, power limit, clock, protocol version, work_rate, power, measured_at.

### 17. Track dead systems aggressively
For every dead network/provider/pool: last_seen, last_price, last_hashrate, last_capacity, shutdown_event, failure_reason.

### 18. Create canonical hardware cohorts
GPU_CONSUMER_HIGH_2026, GPU_DATACENTER_HOPPER, GPU_DATACENTER_BLACKWELL, CPU_HIGH_END_DESKTOP, ASIC_HEAVYHASH_GEN3. Store exact constituents/version.

### 19. Preserve market topology
Not just prices. Every day store: asset, exchange, pair, status, first_seen, last_seen, deposit_enabled, withdrawal_enabled.

### 20. Archive source pages/docs selectively
Store raw response or content hash + snapshot for: pool terms, hardware listings, mining calculator methodology, protocol docs, API docs, fee schedules.

---

## Priority: Top 7 Foundations (Time Compounds Value)

These make virtually everything collected afterward age well:

1. **Permanent IDs + universe snapshots** — survivorship bias prevention
2. **Immutable raw observations** — bitemporal correctness
3. **Bitemporal knowledge/labels** — what was known when
4. **Daily Merkle manifests + timestamps** — provable existence
5. **Experiment/hypothesis registry** — reproducible research
6. **Opportunity-set snapshots** — counterfactual decisions
7. **Source-quality history** — longitudinal data confidence
