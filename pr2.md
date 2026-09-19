# PowPowPow PR2 — Mathematical Hardening

## P0 Math Fixes

### 1. Miner Revenue Formula
**Wrong:**
```python
daily_revenue = (specs['hashrate'] / 1e12) * daily_emission * price
```

**Correct:**
```
R_h = (h_machine / H_network) * E_network * P
```
Revenue = (machine work rate / network work rate) × daily emission × token price

### 2. Remove sell_fraction assumption
`sell_fraction = 0.6` is an assumption, not observation. Store as scenario, not hard data.

### 3. Fix time unit mixing in pressure.py
`miner_exchange_flow_usd_day` compared with aggressive flow from shorter window. All terms must use same time window.

### 4. Fix OFI naming
`ofi_1h = fast.get('ofi_5')` is five-level OFI, not 1-hour. Fix naming.

### 5. Rename required_buy_flow
Current heuristic is not empirically estimated. Reserve name for fitted quantity.

---

## Canonical Seesaw State

For every network/hour:

```
SeesawState
  resource
  demand
  capacity
  utilization
  external_resource_price
  protocol_implied_resource_price
  allocation_wedge
  supplier_margin
  capacity_change
  supply_elasticity
  response_latency
  protocol_subsidy
  user_revenue
  subsidy_dependence
  subsidy_efficiency
  token_price
  market_cap
  emission_pressure
  realization_pressure
  absorption
  seesaw_divergence
```

---

## Key Metrics (20 total)

### 1. Resource Premium
```
RP = protocol_revenue_per_machine_hour / external_rental_per_machine_hour
```

### 2. Allocation Wedge
```
W = π_protocol - π_outside_option
W > 0 → machine should migrate toward protocol
```

### 3. Supply Response Function
```
ΔH_{t+k} = α + Σ β_j ΔW_{t-j} + ε_t
```
Impulse response: profitability increases 50% → how much hashrate enters after 1h, 6h, 1d?

### 4. Supply-Response Half-Life (T50)
Time required for 50% of eventual capacity response.

### 5. Scarcity Persistence
```
SP = ∫₀ᵀ max(W_t, 0) dt
```
How much excess return persisted before supply killed it?

### 6. Seesaw Velocity
```
V = |ΔCapacity| / (Δt × |W|)
```
High velocity = rapid supply response. Low velocity = persistent constraint.

### 7. Constraint Tightness
```
CT = UtilizedCapacity / TotalCapacity
```
How convex does pricing become as utilization → 100%?

### 8. Compute Shadow Price
```
λ_GPU = $/GPU-hour
λ_CPU = $/CPU-hour
λ_ASIC = $/TH/s-hour
```
Compare across all networks.

### 9. Subsidy Efficiency
```
SE = external_market_value_of_produced_work / protocol_subsidy
```
SE = 0.10 → paying $10 for $1 of externally priced resource.

### 10. Subsidy Dependence
```
SD = ProtocolSubsidy / (ProtocolSubsidy + UserPayments)
```
SD = 0.90 → 90% from inflation.

### 11. Machine Revenue Density
```
MRD = $ Revenue / MachineHours
MRD_W = $ Revenue / kWh
```

### 12. Energy Conversion Efficiency
```
ECE = market_value_produced / kWh
```

### 13. Miner Stress / Margin
```
Margin = (Revenue - Cost) / Revenue
```
Costs: electricity + hardware depreciation + pool fees.

### 14. Price → Hashrate Lag
Cross-correlation at k = 1h, 6h, 12h, 1d, 3d, 7d.
Find k* = argmax ρ_k. Capital-allocation latency.

### 15. Hashrate → Price Feedback
Does hashrate increase precede price weakness?
```
Corr(ΔHashrate_t, Return_{t+k})
```

### 16. Creation Pressure
```
CP_1h = ExpectedEmissionUSD_1h / BidDepth_5%
```
One hour of issuance = X% of current 5%-deep bids.

### 17. Realization Pressure
```
RP = Miner→ExchangeUSD_1h / BidDepth_5%
```
Distinguishes: created → paid → moved → deposited → sold.

### 18. Absorption
```
A_t = (AggressiveBuyUSD + NetBidAddition) / (AggressiveSell + MinerExchange)
```
A > 1: demand absorbs. A < 1: supply exceeds.

### 19. Required Buy Flow (Empirical)
Fit: r_{t+h} = β₀ + β₁OFI + β₂MinerFlow + β₃Depth + β₄Spread + β₅Vol + ε
Solve E[r] = 0 for required buy flow.

### 20. Seesaw Divergence
```
Divergence = z(ΔMarketCap) - z(ΔF)
```
Disconnect between financial claim and underlying machine economy.

---

## Missing Raw Fields to Add

- External compute rental benchmarks (stable hardware classes)
- Electricity benchmark series (region + price type)
- Hardware acquisition price observations
- First-party network work rate/difficulty/emission
- Pool/miner distributions where observable
- User-paid revenue vs protocol emissions
- Useful output counts (jobs, GPU-hours, inference, proofs)
- Market L2/trades
- Software/miner/protocol versions

---

## Content Examples

> "PRL H100 profitability just crossed 1.8× the external rental market—but hashrate hasn't responded yet."

> "Kaspa ASIC margins collapsed 32% but hashrate barely moved."

> "One hour of Pearl issuance now equals 46% of the SafeTrade 5% bid book."
