# PowPowPow — Data Garden Dev Plan (current)

> **PowPowPow continuously converts ephemeral compute/crypto reality into a persistent historical record of compute economics.**

That is much stronger than "crypto research site," "mining dashboard," or even "fundamentals terminal."

## The garden

```text
FRAGMENTED REALITY
network state
hashrate
difficulty
emissions
burns
fees
token price
exchange liquidity
hardware benchmarks
electricity prices
GPU rental rates
inference revenue
miner payouts
protocol changes
treasury flows
software releases
marketplace capacity
        ↓
CANONICAL RESOURCE GRAPH
        ↓
VERSIONED TRANSFORMATIONS
        ↓
COMPUTE ECONOMIC STATE
        ↓
PERSISTENT HISTORY
```

General rule for all gardens:

$$
\boxed{
\text{Moat}
\approx
\text{Unique Transformation}
\times
\text{Continuous Collection}
\times
\text{Time}
}
$$

Raw data itself is not the moat; the valuable object is a continuously transformed proprietary measurement whose historical states cannot simply be reconstructed years later. PowPowPow's specific transformation is fragmented resource and market telemetry → **compute economics**.

## What PowPowPow actually measures

Canonical primitive: a **resource opportunity state**. At time \(t\):

```text
resource
+
workload
+
network/protocol
+
location
+
hardware
+
market conditions
        ↓
economic state
```

```json
{
  "timestamp": "2026-09-19T10:00:00Z",
  "resource": {
    "type": "gpu",
    "model": "RTX_4090",
    "region": "US"
  },
  "opportunity": {
    "type": "mine",
    "target": "NETWORK_X"
  },
  "revenue": {
    "gross_usd_day": 4.82
  },
  "costs": {
    "power_usd_day": 1.91,
    "fees_usd_day": 0.14,
    "depreciation_usd_day": 0.73
  },
  "net_usd_day": 2.04,
  "confidence": 0.91,
  "provenance": ["..."]
}
```

The same hardware simultaneously has mine/rent/serve/run/sell/idle routes. The dataset is the **historical opportunity cost of compute** — deeper than any mining calculator.

## Only one layer is the garden

```text
                    POWPOWPOW

              ┌─────────────────┐
              │   DATA GARDEN   │
              │                 │
              │ Resource Graph  │
              │ Historical State│
              │ Provenance      │
              │ Transformations │
              │ Outcomes        │
              └────────┬────────┘
                       │
       ┌───────────────┼────────────────┐
       ↓               ↓                ↓
  KNOWLEDGE        INTELLIGENCE      EXECUTION
  COMPILER          / RESEARCH        AGENTS
       │               │                │
     pages           signals          allocator
     videos          screens          routing
     tools           backtests        execution
     MCP             experiments      receipts
```

The garden is not the website, not the signal engine, not the allocator. Those are outlets. The precious thing is the monotonically accumulating historical state underneath. Feature count is not moat.

## The daily state

Everything converges on an impeccable snapshot per network / hardware / marketplace / economic input:

```text
RAW OBSERVATIONS → canonical IDs → timestamp normalization
→ source reconciliation → economic transformations
→ derived measurements → STATE[t]
```

The product is partly the difference:

$$
\Delta State_t = State_t-State_{t-1}
$$

miner margin compressed / hash economics improved / network demand increased / GPU opportunity cost changed / issuance changed / rental market tightened / AI workload displaced mining. Research and content emerge from the diff.

## Epistemic ladder (never collapse it)

```text
OBSERVATION → DERIVED MEASUREMENT → HYPOTHESIS → EXPERIMENT
→ EMPIRICAL RELATION → DECISION → OUTCOME
```

Never store `QUBIC = BUY` as truth. Preserve observation ("miner revenue per unit compute fell 18%"), derived margin, signal (`miner_pressure = HIGH`), hypothesis (H_017 with n, returns, MAE, regime split), and only then let a separate decision system act. PowPowPow improves without rewriting history.

## Version the transformations, not only the data

Keep `miner_pressure_v1` AND `miner_pressure_v2`, rerun both against immutable observations. Accumulate data history + transformation history + experiment history + outcome history. A scientific instrument, not a dashboard.

## Seesaw made measurable

$$
Innovation \rightarrow \Delta Constraint \rightarrow \Delta ShadowPrice
\rightarrow Capital Allocation \rightarrow Supply Response
\rightarrow Constraint Relaxation
$$

PowPowPow observes one measurable region: new inference model → GPU demand → rental price → mining opportunity cost → hashrate migration → issuance economics → token economics. An empirical laboratory for **how scarce computational resources get allocated**.

## Seed organisms

Qubic forces the ontology to model compute + consensus + AI workload + issuance + burns + external mining revenue. Monero gives CPU commodity compute + privacy utility + RandomX + tail emission. Add organisms that force the ontology to become more general — never "support every coin."

## Autoassign closes the loop

```text
observe → calculate → choose → execute → receipt
→ observe actual result → learn
```

Realized outcome (`expected_net` vs `realized_net` + receipt + prediction error) is ground-truth economic execution data. Substantially harder to copy than scraped economics.

## Compounding moats

```text
L0  RAW HISTORY            historical observations
L1  CANONICAL HISTORY      identity-resolved normalized entities
L2  TRANSFORMED HISTORY    margins, scarcity, pressure, opportunity cost
L3  EXPERIMENT HISTORY     hypotheses + backtests + falsifications
L4  EXECUTION HISTORY      expected versus realized outcomes
L5  AUDIENCE HISTORY       what humans actually cared about
L6  ACTIVE COLLECTION      what new measurements previous layers demand
```

Content is an active-learning sensor: graph anomaly → video → retention signal → higher collection resolution → better metrics → better research.

Content queries over the garden: largest state changes, largest disagreements with price, new historical extremes, new causal relationships, hypothesis confirmations/failures, allocation changes. Headlines come **after real computation**.

## Narrow signals, narrow collection

Ingest only what maps onto physical/economic causality: compute, power, capital, hardware, issuance, revenue, fees, liquidity, supply, demand, allocation. **Price is the thing PowPowPow explains, not the primary thing used to explain price.** Do not collect something merely because it is interesting — collect it because you know what proprietary state transformation it participates in. Adjacent resources (electricity, GPU rental, HBM) enter only when they affect a compute-economic transformation.

## Survivor-bias-proof history

Snapshot live AND dead networks, delisted assets, failed miners, abandoned protocols, broken APIs, marketplace closures, historical hardware. Permanent IDs + point-in-time universes, or backtests are garbage.

## Provenance is the product

Every derived figure answers "why?" down to source observations + transformation code hash + metric version + timestamp + disagreement + confidence. Machine-readable claim + timestamp + provenance + transformation + uncertainty + historical outcomes. MCP exposes the garden; the state must outlive any agent protocol.

## First finished garden

One complete organism: collect → preserve → normalize → transform → derive → hypothesize → backtest → publish → distribute → measure response → agent access → execute one allocation → receipt → learn. Then clone the **garden machinery** (Source, Observation, Entity, Snapshot, Transformation, Metric, Claim, Evidence, Hypothesis, Experiment, Outcome, Decision, Receipt, Outlet, Feedback) — not the domain schema.

## Canonical sentence (polices all future development)

> **PowPowPow is a continuously growing, provenance-preserving historical model of how computational resources are valued, allocated and transformed into economic output.**

Fits: website, explainers, XMR, mining/hardware economics, signals, backtesting, Autoassign, inference markets, content, MCP, downstream trading experiments. Does NOT fit: random crypto news, generic TA, generic coin pages, scraping without a transformation, features that don't enrich the garden. Even if every visible product changes in five years, the garden underneath keeps growing. That is the asset.
