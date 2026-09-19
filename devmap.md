# PowPowPow — Development Map

## Phase Priority

Prove that Seesaw/resource variables add information beyond ordinary crypto beta before expanding the universe.

---

## Engineering Order

1. **Harden warehouse** — timestamp/provenance/recoverability, freeze IDs/schemas
2. **Backfill cheap history** — price, volume, difficulty, hashrate, emission, protocol events, BTC/ETH, electricity, GPU rental, hardware
3. **Canonical Seesaw panel** — single research table everything uses
4. **BTC/market baselines** — establish boring-stuff baseline before Seesaw
5. **First causal Seesaw tests** — profitability→capacity, wedge→allocation, overshoot→returns
6. **Event studies** — identify shocks, show t-7 through t+30
7. **Powfolio** — thesis simulator, not generic optimizer
8. **Content layer** — data → events → stories → analytics → learn

---

## Seesaw Panel Schema

```
seesaw_panel_1h / seesaw_panel_1d

timestamp
asset

# market
price
return
volume
market_cap

# broad market
btc_return
btc_volatility
eth_return

# physical network
capacity
hashrate
difficulty
emission

# economics
revenue_per_resource
electricity_cost
external_resource_value
allocation_wedge
miner_margin

# liquidity
spread
depth
ofi
aggressive_flow

# resource markets
gpu_rental_price
gpu_availability
energy_price

# event state
protocol_event
listing_event
software_event
```

---

## BTC Baseline

For every asset:
```
r_asset,t = alpha + beta_BTC * r_BTC,t + epsilon_t
```

Study residual:
```
r_idio,t = r_asset,t - beta_BTC * r_BTC,t
```

Rolling betas:
- BTC beta 7d / 30d / 90d
- ETH beta
- Crypto market beta
- Residual return
- Residual volatility

Content hook: "PRL is up 18%, but only 3% can be explained by the broader crypto move."

---

## Incremental Value Test

Every feature must pass:
```
M0 = BTC + own price/volume
M1 = M0 + profitability + allocation wedge + hashrate
M2 = M1 + depth + OFI + miner flow
M3 = M2 + protocol/software/events

Does M1 beat M0? → resource data is worth preserving
Does M2 beat M1? → liquidity data is worth preserving
Does M3 beat M2? → event data is worth preserving
```

---

## First Causal Tests (in order)

1. price → profitability
2. profitability → capacity/hashrate
3. allocation wedge → capacity
4. capacity response → future profitability
5. capacity overshoot → future residual returns
6. emission/depth → future residual returns
7. miner flow/depth → future residual returns
8. L2 absorption → future short-horizon returns

---

## Event Studies

Identify shocks:
- profitability > 2σ
- hashrate change > 2σ
- resource premium > 2σ
- GPU availability shock
- emission-pressure shock
- miner-flow shock
- major software/protocol release

Show t-7 through t+30.

---

## Architecture: Resource/Constraint Warehouse

### Shared primitives (domain-agnostic):
```
resource
capacity
utilization
price
lead_time
inventory
supplier
region
demand_proxy
constraint
substitute
downstream_market
```

### Domain packages:
```
core/
  resource_observation
  supplier
  capacity
  utilization
  price_quote
  inventory
  lead_time
  demand_event
  constraint_event
  geography
  methodology

domains/
  pow/           ← PRL, QUBIC, XMR, KAS, etc.
  gpu-cloud/     ← Akash, Clore, Nosana, RunPod
  semiconductors/ ← HBM, NVIDIA, TSMC
  energy/        ← electricity, datacenter power
  agents/        ← inference costs, task markets
```

### Cross-layer Seesaws:
```
HBM scarcity → GPU lead times → GPU rental price → mining opportunity cost
AI inference demand → cloud GPU utilization → rental prices → GPUs leave mining → hashrate
```

---

## Physical Intelligence Constraint Index

Track categories:
```
compute
memory (HBM, DRAM)
energy (grid, datacenter)
networking
fabrication
advanced packaging
cooling
land/grid interconnect
robotics components
```

Estimate:
```
constraint tightness
price acceleration
capacity response
lead-time expansion
substitution pressure
scarcity persistence
```

### Constraint migration:
```
C_t^GPU → C_{t+k}^Power → C_{t+m}^Networking
```

The bottleneck moves. PowPowPow maps it.

---

## Long-term Asset

> A longitudinal map of how increasingly cheap intelligence pushes against expensive physical reality.

Not a crypto analytics site.

---

## Stocks = context, not core moat

- stocks = explanatory/context data (daily/hourly prices, sector ETFs, earnings/capex)
- weird PoW/compute markets = proprietary high-resolution data

Keep moat concentrated. Don't compete with professional equity data firms.

---

## Content Layer (later)

Data → events → stories → analytics → learn.

Audience feedback discovers which data transformations are cognitively useful.
Those become content primitives AND dashboard metrics AND potential trading factors.
