# PowPowPow Canonical Universe V1

> **No machine-readable supplier/miner telemetry → no PowPowPow core dataset.**

## Admission Rule

A system qualifies only if we can observe:
- **Who** is supplying the scarce resource
- **How much** they supply
- **What they earn**
- **How that changes over time**

## Canonical Universe V1 (16 systems)

| System | Scarce Resource | Hard Supplier Data? |
|--------|-----------------|---------------------|
| **QUBIC** | computation / computors | Yes |
| **PRL** | GPU work | Yes |
| **NOCK** | ZK proving work | Yes |
| **QUAN** | CPU/GPU PoW | Yes |
| **TSC** | verified inference | Yes |
| **GNK** | GPU inference | Yes |
| **XMR** | CPU PoW | Yes |
| **TIG** | algorithms + benchmark compute | Yes |
| **TAO** | subnet miners/digital commodities | Yes |
| **AKT** | GPU/CPU capacity | Yes |
| **CLORE** | GPU marketplace + mining | Yes |
| **NOS** | GPU compute | Yes |
| **TFUEL/Theta** | GPU jobs + inference | Yes |
| **FLUX** | compute nodes + PoW | Yes |
| **QRL** | PQ PoW | Yes |
| **KAS** | PoW benchmark/control | Yes (control) |

## Universal Supplier Schema

```text
resource_supplier_snapshot
  timestamp
  network
  supplier_id

  resource_type
  hardware_type
  hardware_model
  hardware_count

  capacity_total
  capacity_available
  capacity_active

  work_units_completed
  work_units_failed

  ask_price_usd
  realized_price_usd

  protocol_reward_native
  protocol_reward_usd

  user_revenue_usd

  power_watts
  estimated_energy_cost_usd

  software_version
  protocol_version
```

## Resource Market Schema

```text
resource_market_snapshot
  timestamp
  network
  resource

  capacity
  utilization

  supplier_count
  HHI

  median_ask
  weighted_realized_price

  protocol_subsidy
  user_revenue

  external_resource_price
```

## Key API Sources

### CLORE
- API: https://clore.ai/api-docs
- GigaSPOT: https://gigaspot-api-docs.clore.ai
- Data: GPU marketplace, asks, bids, utilization

### NOSANA
- API: https://learn.nosana.com/api/intro.html
- Markets: https://learn.nosana.com/api/markets
- Data: GPU markets, hosts, jobs, benchmarks

### THETA
- RPC: https://docs.thetatoken.org/docs/theta-edgecloud-client-rpc-apis
- Data: GPU node prices, jobs, USD earnings

### FLUX
- API: https://docs.runonflux.io/fluxapi
- Production: https://api.runonflux.io
- Data: 15,000+ nodes, benchmarks, economics

### TAO
- Metagraph: https://preview.bittensor.com/docs/query/metagraph
- Emissions: https://www.bittensor.com/docs/concepts/emissions
- Data: Per-subnet miners, validators, emissions

### TIG
- Swagger: https://swagger.tig.foundation
- Data: Algorithms, benchmarks, tracks, blocks

### QUBIC
- RPC: https://docs.qubic.org/api/rpc
- Production: https://rpc.qubic.org
- Data: Ticks, epochs, computors, contracts

### PRL
- RPC: https://github.com/pearl-research-labs/pearl/blob/master/node/docs/json_rpc_api.md
- Mining: https://github.com/pearl-research-labs/pearl/blob/master/node/docs/mining.md
- Data: Blocks, difficulty, pool flows, miner economics

### QUAN
- Mining: https://docs.quantus.com/guides/mining/
- Data: Prometheus metrics, hashrate, GPU efficiency

### TSC
- Docs: https://tensorcash.org/docs
- RPC: https://tensorcash.org/docs/rpc
- Verifier: https://tensorcash.org/docs/verifier/api
- Data: Work units, proofs, validation, rewards

### GNK
- API: https://gonka.ai/docs/host/network-node-api
- Data: Hosts, weights, inference, rewards

### XMR
- RPC: https://docs.getmonero.org/rpc-library/monerod-rpc
- Data: Difficulty, hashrate, emissions, mempool

### QRL
- Explorer: https://docs.theqrl.org/api/explorer-api
- Data: Blocks, emission, reward, mining stats

### KAS
- Docs: https://kaspa.org/build
- Data: 10 blocks/sec, difficulty, hashrate
