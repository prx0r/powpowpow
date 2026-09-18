# PowPowPow Seesaw Filter

The filter is:

> **PowPowPow only tracks systems where a measurable external constraint creates a measurable economic pressure, and where supply responds through some observable physical or cryptographic resource.**

## Inclusion Criteria

A network qualifies only if you can map it onto:

$$
\text{Demand shock}
\rightarrow
\text{binding constraint}
\rightarrow
\text{shadow price}
\rightarrow
\text{capital/resource allocation}
\rightarrow
\text{supply response}
\rightarrow
\text{constraint relaxation}
$$

And crucially, **at least three of those stages must have hard data feeds**, ideally including the resource itself.

## Seesaw Qualification Checklist

A system gets promoted into the core dataset only if it has:

1. **Observable demand**
   Usage, jobs, transactions, inference calls, proofs, rentals, fees.

2. **A binding scarce resource**
   GPU, CPU, ASIC, energy, TEE, storage, bandwidth, proof generation, validator capital, privacy liquidity.

3. **A measurable shadow price**
   Mining profitability, GPU rental $/hr, proof fee, staking yield, resource bid price, difficulty-adjusted reward.

4. **Observable resource allocation**
   Hashrate, GPU count, providers, miner count, validator stake, proving capacity.

5. **Observable supply response**
   More hardware/compute enters after profitability changes.

6. **An external benchmark**
   Electricity, GPU prices, cloud rental prices, ASIC prices, bandwidth/storage prices.

7. **A market price you can join to the above**
   Token price/order book/volume.

**Require 1–5**, and at least one of **6–7** to make it truly useful.

## Core Metrics

### Resource Premium

$$
\text{Resource Premium}
=
\frac{\text{protocol reward per unit resource}}
{\text{external market price per unit resource}}
$$

### Supply Elasticity

$$
\text{Supply Elasticity}
=
\frac{\%\Delta \text{resource capacity}}
{\%\Delta \text{resource profitability}}
$$

## Core External Feeds

```text
energy_price
gpu_spot_price
gpu_cloud_rental
asic_price
hardware_benchmark
shipping/import_cost
interest_rate
```

Every network gets joined against these.

## Seesaw Maps

### PRL
```
PRL demand/price rises
→ H100 mining becomes more profitable
→ GPUs move into Pearl
→ hashrate rises
→ miner rewards/inventory increase
→ exchange sell pressure increases
→ price/difficulty/profitability rebalance
```

### QUBIC
```
QUBIC economics / Aigarth demand
→ compute becomes valuable
→ computors allocate hardware
→ work capacity changes
→ emissions/burn economics change
→ market reprices QUBIC
```

### AKT
```
GPU demand rises
→ H100 rental price rises
→ providers add GPUs
→ available capacity expands
→ utilization falls
→ rental price normalizes
```

### LA (Lagrange)
```
ZK proof demand rises
→ prover capacity becomes constrained
→ price/latency of proving rises
→ operators add GPUs
→ proof throughput rises
→ proof cost falls
```

### PHA
```
demand for attested private compute
→ TEE capacity becomes scarce
→ TEE compute price rises
→ operators deploy TDX/SGX-capable hardware
→ capacity expands
```

### XMR
```
XMR price / transaction demand
→ RandomX mining profitability rises
→ CPUs/hashrate enter
→ difficulty rises
→ miner margins compress
```

## The Real PowPowPow Object

The real PowPowPow object is not the coin. It is the Seesaw.

A coin/network only gets into the core if you can identify and measure:

> **constraint → price → allocation → supply response**

That gives you a genuinely hard boundary and keeps the dataset coherent as you add more systems.
