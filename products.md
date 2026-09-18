# PowPowPow Products — Future Reference

> **PowPowPow = observe. Seesaw = decide. QP/grants = authorize. agents = act. XMRBot = settle privately. receipts/proofs = verify what happened.**

That is much more coherent than separate projects.

---

## Product 1: Autonomous Resource Agent

Inspects the host it is running on, queries PowPowPow, and decides the best allowed action for that machine.

```text
detect:
  Ryzen 7950X
  64 GB RAM
  electricity = $0.09/kWh
  max power = 160W

query PowPowPow:
  XMR expected net = $1.42/day
  QUAN expected net = $0.83/day
  idle compute rental = $0.31/day

policy:
  allowed = [XMR, QUAN]
  min_margin = 10%
  max_switches_day = 2
  settlement_asset = XMR

action:
  mine XMR
```

Bounded grant (no unrestricted authority):

```text
grant:
  action: start_miner
  network: XMR
  max_power_w: 160
  max_duration_h: 12
  wallet: agent_subaddress_04
  auto_swap: false
  expires_at: ...
```

Reuses XMRBot authority model: exact-payload grants, per-agent wallets/subaddresses, replay protection, no generic wallet-send capability.

---

## Product 2: Pow Router

> **What should this machine do right now?**

Actions: mining, renting compute, serving inference, proving, or doing nothing.

H100 agent compares:

```text
PRL mining expected net
vs
Nosana job revenue
vs
Akash lease value
vs
Clore spot value
```

Chooses based on expected return, confidence, liquidity, hardware wear, switching cost, and policy.

API:

```text
POST /allocate

{
  "hardware": {...},
  "constraints": {...},
  "wallet_policy": {...}
}

Response:
{
  "recommended_action": "mine_prl",
  "expected_net_usd_hour": 2.84,
  "confidence": 0.73,
  "reason": {
    "resource_premium": 1.62,
    "difficulty_trend": "stable",
    "sell_pressure": "moderate",
    "liquidity": "sufficient"
  }
}
```

Agent executes only after QP validates the grant.

---

## Product 3: Private Mining Treasury

Machine earns arbitrary assets, treasury policy routes them:

```text
earn PRL
→ retain 20%
→ swap 80%
→ settle into XMR
→ move to dedicated subaddress
→ issue receipt
```

XMRBot = private settlement layer, not mining brain.
Miner/worker gets task-scoped address + constrained execution path.

---

## Product 4: Agent Procurement for Compute

Flip the direction. Agent needs compute:

> "Run this workload privately under $6."

Queries PowPowPow, finds cheapest acceptable resource, XMRBot handles procurement.

```text
discover → route → propose → grant → execute → independent readback → receipt
```

---

## Product 5: MCP for Machine Economics

```text
pow_get_profitability(device)
pow_compare_workloads(device)
pow_get_resource_price(resource)
pow_get_miner_pressure(asset)
pow_get_energy_proxy(region)
pow_get_market_depth(asset)
pow_get_supply_response(asset)
pow_get_best_action(device, constraints)
```

Any Claude/ChatGPT/Goose/OpenCode agent can reason over dataset.

---

## Product 6: Agent Miner OS

Local daemon on Linux exposing:

```text
hardware inventory
wallet state
current task
current miner/process
power draw
thermal limits
earned amount
expected vs realized revenue
```

Self-correcting loop:

```text
PowPowPow predicts $3.10/day
agent mines
realized = $2.47/day
difference logged
model calibration updates
```

Gains **outcome data** from machines actually acting on it.

Execution receipt:

```text
execution_receipt:
  device_fingerprint_hash
  workload
  start_time
  stop_time
  predicted_revenue
  realized_revenue
  energy_used
  rewards_received
  tx_receipt
  software_version
  policy_grant_hash
```

Dataset evolves from historical telemetry → verified execution history.

---

## Product 7: Private Supply Aggregation / MPC

1,000 opted-in machines privately submit:

```text
hardware class
available capacity
minimum acceptable rate
region bucket
power-cost band
```

MPC computes aggregate supply curves without exposing individual hosts.

PowPowPow learns:

> "Approximately 420 H100-equivalent GPU-hours willing to switch into PRL above $2.80/hour."

Real-time **compute supply curve**. Estimates **latent supply response** before hardware migrates.

---

## Product Sequencing

1. **Pow MCP/API** — read-only resource economics
2. **Local Allocation Agent** — recommends what current machine should do
3. **Bounded executor** — starts/stops workloads under exact grants
4. **XMR treasury adapter** — private settlement and task-scoped wallets
5. **Execution receipts** — predicted vs realized economics
6. **Multi-machine controller** — manage a fleet
7. **Private supply aggregation/MPC** — aggregate latent capacity without exposing operators

---

## The Flywheel

```text
public hard data
→ better decisions
→ agents act
→ realized outcomes
→ proprietary execution data
→ better models
→ better decisions
```

Dataset evolves from historical public telemetry → closed-loop machine economy dataset.

That is where the ecosystem becomes genuinely hard to copy.
