# PowPowPow V1 — Strict Miner Telemetry

> **A network only qualifies if we can watch a physically scarce machine resource being allocated in real time, measure the marginal economics of supplying it, and observe supply responding to price/reward.**

## V1 Admission Requirements

1. **Physical resource:** GPU, CPU, ASIC, electricity, storage, bandwidth, TEE.
2. **Live supplier telemetry:** hashrate, machines, jobs, capacity, utilization, difficulty, etc.
3. **Known marginal cost:** power + hardware + rental/depreciation.
4. **Known reward/revenue:** coins/day, $/GPU-hour, $/job, block reward.
5. **Supply response:** more/less machines entering as profitability changes.
6. **Market price:** so we can link the resource economy to the token/order book.

**If one is missing, it isn't V1.**

---

## V1 Universe — 8 Systems

| System | Physical Resource | Live Telemetry | Marginal Cost | Reward | Supply Response | Price |
|--------|-------------------|----------------|---------------|--------|-----------------|-------|
| **PRL** | H100/H200 GPU | Hashrate, pool flows | Power + HW amort | Mining rev | GPU entry/exit | SafeTrade |
| **QUBIC** | CPU compute | Epochs, computors | Power + HW amort | Epoch rewards | Computor changes | SafeTrade |
| **QUAN** | GPU/CPU | Prometheus metrics | Power + HW | Block reward | Miner entry | SafeTrade |
| **XMR** | CPU | Hashrate, difficulty | Power + CPU dep | Block reward | CPU entry | CEX |
| **KAS** | ASIC | Hashrate, difficulty | Power + ASIC dep | Block reward | ASIC entry | CEX |
| **CLORE** | GPU marketplace | Machines, asks/bids | Rental cost | Rental revenue | Provider supply | CEX |
| **AKT** | GPU/CPU capacity | Provider inventory | Rental cost | Lease revenue | Provider supply | CEX |
| **NOS** | GPU compute | Hosts, jobs, pricing | Rental cost | Job revenue | Host supply | CEX |

---

## The Canonical Experiment: PRL

```
miner profitability
→ new miner supply
→ pool payouts
→ exchange inflow
→ SafeTrade L2 pressure
→ price
```

This is the purest PowPowPow Seesaw because every stage is measurable.

---

## Live Card Format

Every V1 system should eventually produce:

```
COIN — HARDWARE

Gross revenue       $X/day
Electricity         $Y/day
Hardware amort.     $Z/day
Net margin          $N/day

Network hashrate    +X% 7d
Difficulty          +X% 7d
Miner issuance      $___/day
Pool→exchange       $___/day

5% bid depth        $___
Required absorption $___/day
```

**If we cannot build that kind of card, it doesn't belong in V1.**

---

## Second Tier (When Telemetry Strengthens)

| System | Why Not V1 |
|--------|------------|
| **TSC** | Inference work is excellent but telemetry not yet mature |
| **GNK** | Host capacity measurable but rewards less clear |
| **NOCK** | Proof generation interesting but economics less mature |
| **THETA** | GPU rental/jobs but less "mineable" feeling |
| **FLUX** | Physical nodes but broader and messier |

---

## Content/Research Only (Not V1)

| System | Why |
|--------|-----|
| **TAO** | Fascinating but heterogeneous subnet commodities, too abstract |
| **TIG** | Algorithmic efficiency is a different Seesaw |
| **LAGRANGE** | Insufficient public prover telemetry |
| **PHA/NIL/OASIS** | Insufficient supplier-market observability |
| **QRL** | Useful PQ dataset but separate category |
| **MCM** | Interesting but too early |
