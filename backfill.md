# PowPowPow — Backfill vs Ephemeral Archive Strategy

## The Core Distinction

> **Backfillable truth** → fetch/rebuild when needed.
> **Ephemeral truth** → archive continuously because time destroys it.

The moat is **not** "we store every number forever." It is:

> **PowPowPow preserves historical state that the underlying systems themselves do not preserve.**

---

## What Can Actually Be Reconstructed

| Data                               | Historical reconstruction       | Should we continuously hoard it? | Why                                    |
| ---------------------------------- | ------------------------------- | -------------------------------: | -------------------------------------- |
| Block history                      | Excellent                       |                     Low priority | Chain is the archive                   |
| Difficulty                         | Excellent for normal PoW chains |                              Low | Derivable from blocks                  |
| Emission/rewards                   | Excellent                       |                              Low | Derivable from chain                   |
| XMR network hashrate               | Excellent estimate              |                              Low | Difficulty / target block time         |
| PRL historical difficulty          | Excellent                       |                              Low | Chain/explorer                         |
| PRL pool block share               | Good                            |                           Medium | Miner labels may change                |
| PRL transfers                      | Excellent                       |                       Low/medium | Chain remains                          |
| PRL miner/exchange classifications | **Not reliably historical**     |                         **High** | Labels/knowledge change                |
| Qubic ticks/epochs                 | Strong                          |                       Low/medium | Query/archive APIs                     |
| KAS difficulty/history             | Strong                          |                              Low | Reconstructable                        |
| OHLCV                              | Excellent                       |                              Low | Many providers                         |
| Individual market trades           | Partial                         |                           Medium | Venue retention varies                 |
| **L2 order book**                  | **Essentially impossible**      |                           **P0** | Gone once updates vanish               |
| Pool worker counts                 | Usually impossible              |                           **P0** | Snapshot state                         |
| Pool advertised hashrate           | Usually difficult               |                           **P0** | Snapshot state                         |
| Stratum jobs/difficulty            | Impossible                      |                           **P0** | Ephemeral                              |
| Akash GPU availability             | Current state                   |                           **P0** | API exposes current provider inventory |
| Clore marketplace/offers           | Current state                   |                           **P0** | No historical endpoint documented      |
| Clore spot bids                    | Current state                   |                           **P0** | Extremely ephemeral                    |
| Nosana host availability           | Current state                   |                           **P0** | Resource-market state                  |
| GPU cloud rental prices            | **Partly backfillable**         |                           Medium | Historical datasets now exist          |
| GPU stockouts/availability         | Poor                            |                         **High** | More valuable than price alone         |
| GPU purchase quotes                | Poor                            |                         **High** | Listings disappear                     |
| Hardware lead times                | Poor                            |                         **High** | Listings disappear                     |
| Electricity prices                 | Often excellent                 |                              Low | Established historical APIs            |
| Protocol releases                  | Excellent                       |                              Low | Git history                            |
| Miner software *deployment*        | Poor                            |                         **High** | Release ≠ adoption                     |
| Active probe latency               | Impossible                      |                           **P0** | Only exists when measured              |

---

## Reconstructable Layer — Backfill When Needed

### XMR
- Blocks, difficulty, estimated hashrate, reward, fees, emission
- Monero RPC `get_block_headers_range` returns historical data for arbitrary heights

### PRL
- Blocks, difficulty, estimated hashrate, emission
- PearlTrack exposes full address histories, pool labels, transaction classifications

### QUBIC
- Ticks, epochs, computors, transactions, rewards/burns
- Official Query API + go-archiver provide historical access

### KAS
- Blocks, DAA/difficulty, estimated hashrate, emissions

### All assets
- OHLCV (many providers)
- Historical trades wherever available

### External
- Electricity (Electricity Maps `/past`, `/past-range`)
- GPU rental daily history (Price of Compute API)
- Hardware releases (git history)
- Protocol releases (git history)

---

## Ephemeral Archive — Start the Clock NOW (September 2026)

### Exchange L2 (P0)
- SafeTrade L2 order book snapshots
- Gate/CoinEx L2 where relevant
- **Reason:** Once WebSocket updates vanish, historical book is gone

### Pool State (P0)
- Pool worker counts
- Pool reported hashrate
- Stratum job streams
- **Reason:** Snapshot state, never reconstructed

### Compute Marketplaces (P0)
- Akash provider snapshots (GPU models, total/active/available/pending)
- Clore full marketplace (every server, price, availability, rented flag)
- Clore spot order state
- Nosana host/market state
- **Reason:** Current state only, no historical endpoints

### GPU Availability (P0)
- GPU availability/stockouts
- Hardware marketplace listings
- Lead times
- **Reason:** Listings disappear

### Active Probes (P0)
- Pearl Stratum latency
- Qubic tick propagation
- Akash/Clore quote availability
- Exchange event arrival times
- **Reason:** Only exists when measured

### Entity Knowledge (High)
- Our evolving address/entity labels
- Pool→miner→exchange classifications
- Exchange wallet knowledge
- **Reason:** Labels change over time

---

## Point-in-Time Knowledge (Subtle Moat)

Even if something can be reconstructed, our version may still matter:

```text
entity_id
label
valid_from
valid_to

known_at
superseded_at
```

Example: PearlTrack calls address `abc` unknown today. Three months later it recognizes it as SafeTrade. If we rewrite history, backtests "know" the exchange address before anyone did.

Same for:
- Hardware benchmark knowledge
- Pool labels
- Exchange labels
- Software-performance estimates

---

## Warehouse Structure

```
warehouse/
    canonical_backfill/          # Reconstructable, low-priority collection
        blockchain/             # Block data, difficulty, emission
        price/                  # OHLCV, historical trades
        electricity/            # Grid prices, LMP
        gpu_price/              # Historical GPU rental/purchase

    ephemeral_archive/          # Time-sensitive, P0 collection
        exchange_l2/            # SafeTrade/Gate/CoinEx order books
        pool_state/             # Worker counts, reported hashrate
        stratum/                # Job streams, difficulty changes
        compute_marketplaces/   # Akash/Clore/Nosana snapshots
        gpu_availability/       # Stockouts, listings, lead times
        hardware_market/        # Purchase quotes, availability
        probes/                 # Active latency measurements

    knowledge/                  # Point-in-time entity knowledge
        entities/               # Address/entity classifications
        labels/                 # Pool/miner/exchange labels
        protocol_events/        # Releases, parameter changes

    derived/                    # Computed from raw data
        seesaw_state/           # Margin, wedge, absorption
        factors/                # Backtest features
        backtests/              # Experiment results
```

---

## What We Can Backfill Right Now

### Immediate backfill job:
```text
XMR: blocks, difficulty, hashrate, reward, fees, emission
PRL: blocks, difficulty, hashrate, emission, miner/pool identities, pool block share, transparent flows
QUBIC: ticks, epochs, computors, transactions, rewards/burns
KAS: blocks, DAA/difficulty, hashrate, emissions
All: OHLCV, historical trades
External: electricity, GPU rental daily history, hardware releases, protocol releases
```

### Forward-only collectors to start now:
```text
SafeTrade L2 → every update archived
Gate L2 where relevant
Akash provider snapshots → every 5 min
Clore marketplace → every 5 min
Clore spot bids → every 5 min
Nosana host state → every 5 min
Pool worker counts → every 5 min
Pool reported hashrate → every 5 min
Stratum jobs → continuous
GPU availability → every hour
Hardware listings → every hour
Active probes → continuous
Entity labels as-known-at-time → continuous
```

---

## V1 Backtest Roadmap

| Stage | Test                           |        Can run historically now? |
| ----- | ------------------------------ | -------------------------------: |
| 0     | TA/price baselines             |                          **Yes** |
| 1     | Price → hashrate/difficulty    |                   **Mostly yes** |
| 2     | Profitability → hashrate       |                       **Partly** |
| 3     | Resource wedge → capacity      | **Need external resource joins** |
| 4     | Supply-response latency        |  **Yes/partial depending chain** |
| 5     | Creation pressure → returns    |      **Forward only because L2** |
| 6     | Miner flow → market pressure   |        **PRL partial + forward** |
| 7     | Absorption → returns           |                      **Forward** |
| 8     | Mining vs rental allocation    |                **Forward-heavy** |
| 9     | Cross-market compute migration |                      **Forward** |
| 10    | Seesaw Powfolio factors        |         **After enough history** |
| 11    | Protocol/software shock studies|                   **Mostly yes** |

---

## Canonical Backtest Hypotheses (A-K)

### A — Price Creates Machine Incentive
$$\Delta Margin_t = f(\Delta P_t)$$
Sanity test. Required: token price, emission, difficulty, hardware work rate, opportunity cost.

### B — Resource Premium Predicts Supply (Canonical Seesaw)
$$\Delta Capacity_{t+k} = \alpha + \beta W_t + \epsilon$$
Where $W_t$ = protocol revenue/resource hour - external revenue/resource hour.
Test across 1h, 6h, 12h, 1d, 3d, 7d lags.

### C — Response Half-Life
After profitability shock ($W_t > 2\sigma_W$), measure:
$$R(k) = \frac{Capacity_{t+k} - Capacity_t}{Capacity_t}$$
Find $T_{50}$ (time to half response). Compare: PRL GPUs vs XMR CPUs vs KAS ASICs.

### D — Scarcity Persistence
$$SP = \int_{t_0}^{t_1} \max(W_t, 0) dt$$
How long until competition eliminates resource premium?

### E — Price → Hashrate Causal Latency
$$L_{P \to H} = \arg\max_k Corr(Return_t, \Delta Hashrate_{t+k})$$

### F — Profitability > Price as Supply Predictor
Compare: $\Delta H_{t+k} = f(Return_t)$ vs $\Delta H_{t+k} = f(MiningMargin_t)$
If Seesaw is right, profitability explains supply better than price alone.

### G — Hashrate Overshoot → Future Return
$$HashrateOvershoot = H_t - \hat{H}_t$$
Test if too much hardware → structural selling → poorer subsequent returns.

### H — Creation Pressure
$$CreationPressure_t = \frac{NewTokens_t \times Price_t}{BidDepth_{5\%,t}}$$
Test against future return, spread, volatility, bid depletion, OFI.

### I — Miner Realization
$$RealizationRatio = \frac{MinerOriginatedExchangeFlow}{Emission}$$
Do miners hoard during rallies or dump immediately?

### J — Absorption
$$Absorption = \frac{AggressiveBuyUSD + BidAdds - BidCancels}{AggressiveSellUSD + MinerExchangeFlow}$$
Test at 1m, 5m, 15m, 1h, 4h, 24h horizons.

### K — Required Buy Pressure
Fit: $r_{t+h} = \beta_0 + \beta_1 OFI_t + \beta_2 MinerFlow_t + \beta_3 Emission_t + \beta_4 Depth_t + \beta_5 Spread_t + \beta_6 Vol_t + \epsilon$
Solve for marginal buy-flow where $E[r_{t+h}] = 0$.

---

## Cross-Resource Experiments (Future)

### Mining vs Renting
$$W^{PRL}_t = NetPRLRevenue_t - CloudRentalRevenue_t$$
Does $W^{PRL} > 0$ → PRL hashrate ↑, Akash capacity ↓, Clore available GPUs ↓?

### Conservation of Compute
$$C_{total} = C_{mining} + C_{rental} + C_{inference} + C_{idle}$$
When PRL profitability explodes, does decentralized rental availability fall?

### Cross-Network Resource Competition
$$RelativeWedge_{PRL,QUAN} = Margin_{PRL} - Margin_{QUAN}$$
Does this predict capacity ratio changes?

### Opportunity-Set Backtest
$$O_{h,t} = \{\pi_{PRL}, \pi_{QUAN}, \pi_{Clore}, \pi_{Akash}, ...\}$$
$$AllocationEfficiency = 1 - \frac{\pi_{best} - \pi_{observed}}{|\pi_{best}|}$$
Study market efficiency for machines.

### Resource-Market Supply Curves
$$Price = f(Utilization)$$
Is GPU pricing convex above 90% utilization?

### External Resource Shocks
$$\Delta ElectricityPrice \rightarrow \Delta MiningMargin \rightarrow \Delta Hashrate$$
$$\Delta CloudGPUPrice \rightarrow \Delta MiningAllocation$$

### Protocol/Software Shock Studies
When new miner version / algorithm / parameter change occurs, measure:
$\Delta Efficiency$, $\Delta Hashrate$, $\Delta MinerConcentration$, $\Delta Price$

### Cross-Exchange Experiments
$$L_{AB}(k) = Corr(r^A_t, r^B_{t+k})$$
Which venue leads? Does OFI at Gate predict SafeTrade returns?

---

## Validation Methodology

### Walk-forward only
```text
Jan–Mar → Apr
Jan–Apr → May
Jan–May → Jun
...
```

### Bitemporal requirement
Every feature must satisfy: $observed\_at \le prediction\_time$
not merely: $event\_time \le prediction\_time$

### Purged/embargoed testing
24h target horizon → purge 1 day around split.

### Transaction reality
Use actual book for execution: spread, slippage, fees, partial fill, depth, latency.

### Capacity constraints
Report PnL(Q) for $100, $500, $1k, $5k, $10k.

### Baselines required
Compare against: random, buy-and-hold, momentum, mean reversion, volume, RSI, volatility, market beta, BTC return.

### Event studies before ML
Use event studies for: resource premium > 2σ, hashrate jump > 2σ, difficulty jump, utilization > 90%, creation pressure > 2σ, pool share shift > 2σ, GPU price spike, miner flow spike.

---

## Data Sources

| Source | What it provides |
|--------|------------------|
| Monero RPC | Historical block headers, difficulty, rewards |
| PearlTrack API | Address histories, pool labels, classifications |
| Qubic Query API + go-archiver | Historical epochs, computors, ticks |
| Price of Compute API | Full daily GPU median prices |
| GPUs.io API | Historical per-GPU prices |
| Electricity Maps | Historical grid prices, LMP |
| Clore API | Current marketplace (no historical) |
| Akash API | Current provider GPU inventory |
| MiningBoard Pool API | Pool/network hashrate, miners |
| Gate WebSocket v4 | L2 with sequence IDs |
