# PowPowPow Vision — What This Actually Is

> **PowPowPow answers one question: what should this machine do right now?**

Everything else is downstream of that.

---

## The Core Loop

```
you have hardware
        ↓
POW observes: what is compute worth right now?
        ↓
POW recommends: mine XMR, rent GPU, serve inference, idle
        ↓
agent acts (bounded grant, exact payload)
        ↓
POW measures: predicted vs realized
        ↓
better models, better decisions
```

This is the product. Not a dashboard. Not a terminal. Not a trading bot.

**An intelligence layer that turns hardware into revenue.**

---

## XMR as the Golden Child

XMR is the right first organism because:

1. **Privacy is the settlement rail.** Every other mining reward eventually
   routes through XMR for private custody. XMR is the unit of account for
   the machine economy.

2. **Tail emission is forever.** 0.6 XMR/block, 720 blocks/day, 432 XMR/day.
   Predictable, auditable, never ends. The security budget is a known constant.

3. **RandomX is CPU-commodity.** No ASICs, no GPU farms. Every laptop, every
   homelab box, every edge device can mine it. The supply curve is the sum
   of all idle CPU cycles globally.

4. **Mature pool ecosystem.** P2Pool, localmonero, p2pool.observer — we can
   measure miner concentration, pool share, fee rates, mempool pressure.

5. **The reference case.** If POW can't explain XMR price through fundamentals,
   it can't explain anything. XMR is the control group.

### What "perfect for XMR" means

```
EXOGRAPHIC (what tao.app does for TAO):
- Live hashrate + difficulty + hashprice
- Miner revenue per day (USD)
- Security spend / transaction
- Fee market pressure
- Mempool depth + fee estimation
- P2Pool miner distribution
- Block reward vs transaction fee ratio
- Hashrate price elasticity (how does difficulty respond to price?)
- Miner capitulation/euphoria signals
- Hardware profitability by model (RTX 4090 vs Ryzen 7950X vs EPYC)

POW ADDS (what nobody else has):
- Historical miner sell burden (emission × sell fraction / bid depth)
- Absorption ratio (volume / issuance)
- Required buy flow (how much buying stood still)
- Miner margin z-score across all tracked chains
- Realized vs predicted outcome tracking
- Cross-chain comparison (XMR security spend vs QUBIC subsidy/compute)
```

tao.app shows you what happened.
POW shows you **why it happened** and **what happens next**.

---

## The Homelab Question

This is the killer use case that nobody else is building for.

> "I have a Ryzen 7950X, 64GB RAM, and a GTX 1080 Ti sitting idle.
> What should I do with it?"

Current answers:
- "Mine Monero" — maybe, but is that optimal?
- "Sell it" — but the hardware already exists, sunk cost
- "Run an LLM" — but electricity costs more than API calls
- "Do nothing" — the default, and usually wrong

**POW's answer:**

```
detect hardware:
  CPU: Ryzen 7950X (16C/32T, RandomX ~14k H/s)
  GPU: GTX 1080 Ti (11GB, CUDA compute)
  RAM: 64GB DDR4
  Electricity: $0.09/kWh
  Internet: 100 Mbps

query garden:
  XMR mining: $1.42/day net (after electricity)
  PRL mining: $0.83/day net
  QUAN mining: $0.67/day net
  GPU rental (Clore): $0.41/day
  Idle compute (Akash): $0.31/day
  LLM inference: $0.28/day (local Llama 8B)

recommend:
  mine XMR (highest risk-adjusted return)
  secondary: mine QUAN if XMR difficulty spikes
  tertiary: rent GPU if spot price > $0.50/hr

policy:
  min_margin: 10%
  max_switches_day: 2
  settlement: XMR subaddress
  auto_swap: false
```

This is **product 1 from products.md** — the Autonomous Resource Agent.

### What makes this defensible

1. **Historical outcome data.** POW predicted $1.42/day, machine mined,
   realized $1.28/day. Prediction error logged. Model improves.
   Nobody else has this feedback loop.

2. **Cross-hardware benchmarks.** Not theoretical specs — actual measured
   hashrate/power for each hardware model on each algorithm.

3. **Fleet awareness.** 10 homelab boxes reporting in. POW knows:
   "420 H100-equivalent GPU-hours willing to switch into PRL above $2.80/hr."
   That's a real-time compute supply curve.

4. **Settlement through XMR.** Private, fungible, censorship-resistant.
   The machine earns, settles, and the operator never touches an exchange.

---

## Trading & Rebalancing

The UK stocks work connects here. The insight is:

> **Mining economics IS investing economics.**

A miner's decision to mine coin A vs coin B is the same decision as
an investor's allocation to asset A vs asset B. The difference is:

- Mining has real costs (electricity, hardware, pool fees)
- Mining has measurable supply response (hashrate follows price)
- Mining has observable flows (miner wallets → exchanges)

POW can build a **fundamental valuation model** that works for both:

```
FOR MINING:
  expected_return = f(emission, price, difficulty, electricity, hardware_cost)
  actual_return = realized - cost
  signal = expected / actual (calibration quality)

FOR INVESTING:
  fair_value = f(issuance, absorption, demand, security_spend)
  market_value = spot_price
  signal = fair_value / market_value (premium/discount)
```

The UK stocks connection is the same framework applied to equities:

```
POW for mining: "Is XMR fairly valued relative to its security spend?"
POW for stocks: "Is this company fairly valued relative to its earnings?"
POW for compute: "Is this GPU rental fairly priced relative to its utility?"
```

The garden learns valuation across all three domains simultaneously.

### What this means for the devplan

Don't build a separate trading system. Build a **valuation engine** that
works for mining, investing, and compute allocation. The signals are the
same:

- issuance pressure (new supply vs absorption)
- flow analysis (who's buying, who's selling)
- fundamental momentum (usage growth vs price growth)
- mean reversion (overshoot detection)

XMR is the calibration asset. If the model can't explain XMR price,
it can't explain anything.

---

## The Three Layers

```
LAYER 1: OBSERVE (this is what we have)
  collect time-series data
  normalize, transform, derive signals
  archive raw bytes forever
  provenance on every number

LAYER 2: RECOMMEND (this is the next step)
  "what should this machine do right now?"
  bounded grants, exact payloads
  XMR settlement
  outcome tracking

LAYER 3: ALLOCATE (this is the endgame)
  fleet of machines
  private supply aggregation
  compute supply curves
  cross-chain resource routing
  UK stocks as a correlated allocation surface
```

Layer 1 is 60% done (garden collecting, signals v1 live, site live).
Layer 2 is 0% done (needs executor, XMRBot integration, receipts).
Layer 3 is conceptual only (needs 1000+ machines, MPC, fleet controller).

---

## What "tao.app but for XMR" Means

tao.app shows:
- Live network stats
- Subnet performance
- Validator economics
- Inference metrics
- Price charts

POW for XMR should show ALL of that PLUS:

- **Security spend**: USD value securing the network per day
- **Miner margin**: network-share profitability by hardware class
- **Hashprice**: revenue per hash per day (trending)
- **Fee market**: mempool pressure, fee estimation, priority
- **P2Pool distribution**: miner decentralization metrics
- **Buy pressure required**: how much buying needed to absorb emission
- **Miner sell burden**: estimated vs measured selling
- **Hardware frontier**: what's the cheapest hardware to mine XMR today?
- **Difficulty response**: how quickly does hashrate follow price?
- **Cross-chain comparison**: XMR security spend vs QUBIC, PRL, NOCK
- **Historical extremes**: "hashrate is at 6-month low relative to price"
- **Prediction tracking**: "POW predicted $1.42/day, realized $1.28/day"

The last three are what make POW different from any existing XMR dashboard.
Nobody else tracks their own prediction accuracy over time.

---

## Priority: Get XMR Right First

The devplan should be:

```
PHASE 1 (now → 30 days):
  XMR as the reference organism
  - Full XMR analytics (like tao.app but deeper)
  - Hardware profitability benchmarks (actual measured, not theoretical)
  - Miner sell burden + absorption ratio
  - Prediction tracking (expected vs realized)
  - Daily STATE with Parquet
  - 30 days of history → first meaningful backtests

PHASE 2 (30 → 60 days):
  Second organism: QUBIC or PRL
  - Same framework applied to a different compute paradigm
  - Cross-chain signals emerge
  - Supply curve comparison

PHASE 3 (60 → 90 days):
  Executor: "what should this machine do?"
  - Bounded grants
  - XMR settlement via XMRBot
  - Receipt tracking
  - Outcome data feeds back into models

PHASE 4 (90+ days):
  Fleet + compute supply aggregation
  - Multiple machines reporting in
  - MPC for private capacity discovery
  - Cross-chain resource routing
  - UK stocks correlation analysis
```

XMR is the proving ground. If the model works for XMR, it works for
everything. If it doesn't work for XMR, nothing else matters.

---

## The Canonical Sentence (refined)

> **PowPowPow is a continuously growing, provenance-preserving historical
> model of how computational resources are valued, allocated and transformed
> into economic output — answering the question: what should this machine
> do right now?**

The garden is the asset. The recommendation engine is the product.
XMR is the proof.
