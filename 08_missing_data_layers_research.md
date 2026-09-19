# PowPowPow — Missing Data Layers Research

## The Thesis

PowPowPow = data/research infrastructure for weird compute-heavy crypto.

Content is distribution for the data layer, not the product itself.

The moat is the normalized dataset. For every chain you track, collect the same canonical fields. Then derive metrics nobody else publishes.

---

## The Biggest Opportunity

The biggest opportunity is **not more coins**. It is adding a few upstream hard-data layers that let you explain *why* miner/resource economics move before price does.

The strongest missing layer is **miner microstructure**.

---

## 1. Miner Microstructure — Pool + Worker + Stratum Telemetry

Public pool APIs can expose network/pool hashrate, miner counts, blocks, payments, and even per-wallet/worker information. MiningBoard's API, for example, exposes live pool/network hashrate, miners, blocks, payments and wallet-level miner data, including Pearl. Pearl's Stratum protocol itself exposes jobs, targets, difficulty and worker authorization, so you can collect job cadence and difficulty changes directly rather than only polling a block explorer.

### Pool snapshot schema:

```text
mining_pool_snapshot
  pool_id
  network
  event_time

  pool_hashrate
  network_hashrate
  miner_count
  worker_count

  pool_difficulty
  payout_scheme
  pool_fee
  minimum_payout

  blocks_24h
  expected_blocks_24h
  observed_effort

  payouts_native_24h
```

### Stratum probe schema:

```text
stratum_job
  pool
  received_at

  job_id
  chain_height
  target
  difficulty

  job_interval_ms
  reconnect
  stale_job
```

### Derived metrics:

```text
WorkerGrowth_t
PoolShareMigration_t
JobDifficulty_t
```

Compare against profitability. This lets you see **machines joining/leaving before network-wide hashrate statistics fully reflect it.**

---

## 2. GPU Availability (Not Merely GPU Price)

A price of `$2/H100-hour` means very different things when there are 5,000 H100s available versus practically none.

There are now public APIs exposing current GPU availability as well as prices. GPU Finder exposes per-model/provider availability and a seven-day availability history; its availability collector runs hourly. GPUs.io exposes normalized spot/on-demand pricing across 20+ clouds and includes current availability state. Price of Compute exposes not only historical GPU prices but a broader compute index, spot discount, repricing events and even commodity inputs to a GPU-hour.

### Archive schema:

```text
gpu_market_observation
  timestamp

  gpu_model
  provider
  region

  price_usd_gpu_hour
  pricing_type

  availability
  available_units   # where exposed
  node_size

  provider_count
```

### Derived metric — Compute Scarcity:

$$
CS =
PriceZ + AvailabilityTightnessZ
$$

where:

$$
AvailabilityTightness =
1-\frac{AvailableCapacity}{ObservedCapacity}
$$

This is much more Seesaw-like than price alone.

---

## 3. Hardware Lead Times

If H100 prices spike, new supply cannot appear instantly.

The physical lag is:

```text
order GPU
→ manufacturer/channel
→ shipping
→ rack/power
→ network
→ machine online
```

Current suppliers are publishing wildly different lead times depending on whether inventory is physically held; one current market source reports roughly 7 days for held H100 HGX stock, ~10 days for H200, while some B300 channel orders extend toward 50 days.

### Schema:

```text
hardware_supply_quote
  timestamp
  hardware_model

  unit_price
  quantity_available
  condition

  region
  lead_time_days

  source
```

### Derived metrics:

$$
PhysicalSupplyLag_t
$$

$$
ScarcityPersistence
\approx
f(ResourcePremium, LeadTime)
$$

---

## 4. Electricity Constraint Prices

National electricity averages aren't where the real marginal constraint lives.

CAISO publishes **5-minute locational marginal prices** by node, including separate energy, congestion and loss components; it also exposes explicit transmission-constraint shadow prices. That is literally a market publishing **shadow prices of physical constraints**.

For broader US grid state, EIA provides hourly balancing-authority demand, forecasts, net generation and interchange.

### Schema:

```text
power_market
  event_time

  grid
  node
  region

  lmp_usd_mwh

  energy_component
  congestion_component
  loss_component

  constraint_id
  constraint_shadow_price

  demand
  generation
```

### Causal chain:

$$
EnergyConstraint
\rightarrow
MiningMargin
\rightarrow
HashrateMigration
$$

---

## 5. Cross-Exchange Price Discovery

SafeTrade alone tells you local pressure. Multiple venues tell you where information appears first.

Gate is especially useful because its L2 feed provides sequence IDs explicitly designed for correct local order-book reconstruction.

### Schema:

```text
exchange_tick
  timestamp
  asset
  exchange

  mid
  spread
  depth_1pct
  OFI
  aggressive_flow
```

### Derived metrics — Price discovery lead/lag:

$$
Corr(r_A(t),r_B(t+k))
$$

Find:

$$
k^* =
\arg\max Corr
$$

You may discover:

> Gate price leads SafeTrade by 14 seconds, but SafeTrade miner-selling pressure predicts Gate 5 minutes later.

---

## 6. Pool Migration as Signal

Once you archive all identifiable pools:

```text
pool_share
miner_count
worker_count
block_share
payout volume
```

you can calculate:

$$
HHI_{pool}
=
\sum_i share_i^2
$$

and:

$$
PoolMigration_t =
\sum_i |share_{i,t}-share_{i,t-1}|
$$

Miner migration could indicate software efficiency differences, fee changes, payout problems, geographic issues, miner entry, or large farm reallocations.

---

## 7. Mining Software Versions

Hardware hasn't changed, token price hasn't changed, electricity hasn't changed—but a miner release improves work rate 18%. Economically that acts like suddenly creating 18% more hardware.

### Schema:

```text
miner_software_release
  released_at

  network
  software
  version
  commit

  hardware
  benchmark_before
  benchmark_after

  power_before
  power_after
```

### Derived metric:

$$
AlgorithmicSupplyShock
=
\frac{WorkRate_{new}}
{WorkRate_{old}}-1
$$

---

## 8. ASIC Market Pricing

For KAS this matters a lot. ASIC Miner Value currently tracks model, algorithm, hashrate, power, pricing and live profitability across miners.

### Schema:

```text
asic_quote
  timestamp

  manufacturer
  model
  algo

  hashrate
  power

  price
  release_date
```

### Derived metrics:

$$
ASICPayback =
\frac{HardwarePrice}
{ExpectedNetProfitDay}
$$

$$
ASICCapitalPressure =
ExpectedMiningReturn
-
RequiredCapitalReturn
$$

---

## 9. Active Probes

Don't only consume APIs. Operate tiny measurement agents.

Examples:

```text
Pearl:
  connect to several Stratum pools
  timestamp jobs
  measure latency
  record difficulty changes

Qubic:
  query multiple RPC nodes
  measure tick propagation

Akash/Clore:
  issue identical capacity searches
  record quote availability

Exchanges:
  connect from same infrastructure
  measure event arrival times
```

### Schema:

```text
probe_observation
  probe_id
  probe_region
  target
  request_sent_at
  first_byte_at
  event_received_at
  result
```

### Derived metric — Causal Latency:

$$
CausalLatency
=
t_{\text{market reaction}}
-
t_{\text{physical signal}}
$$

Which is basically the thesis that:

> alpha = lower causal latency.

---

## 10. Record Stockouts

If an API says `H100 = unavailable`, store it. Absence is data.

### Derived metrics:

```text
availability_probability_30d
stockout_duration
time_to_restock
```

$$
Scarcity =
Price
+
StockoutFrequency
+
LeadTime
$$

---

## 11. Protocol Rules as Data

Store machine-readable:

```text
protocol_parameter
  event_time
  network

  parameter
  old_value
  new_value

  activation_height

  source_commit
```

Examples: emission divisor, block reward, difficulty algorithm, minimum payout, pool fee, work definition, model version, verification threshold.

Then every structural break in historical metrics can be automatically explained.

---

## 12. Counterfactual Resource Allocation

Once you have:

```text
PRL profitability
XMR profitability
KAS profitability
GPU rental prices
CPU rental prices
electricity
hardware price
hardware availability
```

you can calculate not just what miners *did*, but what a rational machine *could have done*.

### For each hardware class:

$$
OpportunitySet_{h,t}
=
\{
\pi_{PRL},
\pi_{XMR},
\pi_{QUAN},
\pi_{Clore},
\pi_{Akash},
\pi_{Nosana}
\}
$$

Then:

$$
BestAlternative_{h,t}
=
\max_i(\pi_{i,t})
$$

and:

$$
AllocationRegret =
\pi_{best} - \pi_{chosen}
$$

This eventually tells you:

> H100 miners stayed on Pearl for 13 hours after Akash became 24% more profitable.

or:

> XMR miners appear vastly less price-elastic than GPU miners.

---

## Priority Ranking

### P0 — start collecting ASAP because history disappears:

1. Pool + worker + payout telemetry
2. Stratum job/difficulty feeds
3. GPU availability + stockouts
4. GPU rental price snapshots
5. Hardware spot inventory + lead times
6. SafeTrade/Gate/CoinEx L2
7. Software/miner version events

### P1 — huge explanatory value:

8. Nodal electricity prices + grid constraint shadow prices
9. ASIC market quotes
10. Protocol parameter history
11. Active network probes/latency
12. Pool concentration/migration

### P2 — derived later from the above:

13. Supply elasticity
14. Supply-response half-life
15. Resource allocation wedge
16. Scarcity persistence
17. Causal latency
18. Allocation regret
19. Subsidy efficiency
20. Seesaw divergence

---

## The Big Realization

The biggest realization is that you can build something broader than a crypto dataset.

You can build:

> **a historical database of how scarce computation responds to incentives.**

Crypto networks are just unusually transparent experimental markets sitting on top of CPUs, GPUs, ASICs and electricity.

Then the Post-AGI Seesaw becomes empirical:

$$
\text{Demand}
\rightarrow
\text{Physical constraint}
\rightarrow
\text{Shadow price}
\rightarrow
\text{machine allocation}
\rightarrow
\text{supply response}
\rightarrow
\text{constraint relaxation}
$$

And because most of those intermediate observations disappear, **time genuinely compounds the moat**.

---

## Data Sources

| Source | What it provides |
|--------|------------------|
| MiningBoard Pool API | Pool/network hashrate, miners, blocks, payments, wallet-level data |
| Pearl Stratum Protocol V1 | Jobs, targets, difficulty, worker authorization |
| GPU Finder API | Per-model/provider availability, 7-day history, hourly collection |
| GPUs.io API | Normalized spot/on-demand pricing across 20+ clouds |
| Price of Compute API | Historical GPU prices, compute index, spot discount, repricing events |
| Strategic Supply Partners | GPU lead times, live inventory feeds |
| CAISO OASIS API | 5-minute LMP by node, energy/congestion/loss components, shadow prices |
| EIA Open Data | Hourly balancing-authority demand, forecasts, net generation |
| Gate WebSocket v4 | Sequence-ID L2 feed for order-book reconstruction |
| ASIC Miner Value | Model, algorithm, hashrate, power, pricing, profitability |
