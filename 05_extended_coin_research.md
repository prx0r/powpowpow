# PowPowPow — Extended Coin Universe

Yes. **The rule should be: start recording anything that is hard or impossible to reconstruct later.** SafeTrade is ideal because you already have one common market venue, but I'd add a handful of external networks now specifically because their historical state will compound in value.

## The Universe

### SafeTrade Experimental Core
```text
QUBIC  — useful PoW
PRL    — proof-of-useful-work
NOCK   — ZK-PoW
QUAN   — post-quantum PoW
TSC    — proof-of-inference
GNK    — compute marketplace
XMR    — mature PoW control
```

### External Comparison Set
```text
TAO   — intelligence-market benchmark
KAS   — high-throughput industrial PoW
QRL   — post-quantum PoW benchmark
ZEPH  — monetary/reserve PoW experiment
ALPH  — sharded PoW
ERG   — mature GPU PoW / miner economics
XTM   — multi-algorithm PoW experiment
```

---

## TAO (Bittensor)

Highest-priority non-SafeTrade addition. Economically perfect for PowPowPow: subnets produce compute, inference, storage, prediction and other "digital commodities," validators score them, and TAO emissions are allocated according to subnet economics.

Bittensor's emission mechanism changed materially in June 2026, reverting to price-based subnet emissions with additional weighting factors.

### Archive per subnet per block/epoch:
```text
subnet_id
timestamp
tao_price
alpha_price
ema_price
tao_reserve
alpha_reserve
tao_emission
alpha_emission
miner_emission
validator_emission
owner_emission
tao_staked
alpha_staked
miner_burn
root_proportion
active_miners
active_validators
weights
incentives
dividends
```

### Subnet product table:
```text
subnet_id
product_type  # inference, compute, VPN, prediction, storage
description
active_miners
quality_score
```

### Data sources:
- Archive node for historical state (lite nodes only retain ~300 blocks)
- Bittensor docs: https://www.bittensor.com/docs
- Subnet explorer APIs

---

## KAS (Kaspa)

Mature enough for control, technically unusual enough to belong. Nodes retain historical **pruning points** providing daily difficulty samples back through mainnet. Moved to **10 blocks/sec** — extraordinarily rich mining microstructure.

### Archive:
```text
timestamp
daa_score
block_count
difficulty
estimated_hashrate
blue_score
blue_work
block_rate
orphan/red_rate
reward
fees
tx_count
mempool
```

### ASIC economics:
```text
asic_model
firmware
hashrate
power_w
purchase_price
KAS_day
revenue_day
energy_cost_day
margin_day
```

### Data sources:
- Kaspa Wiki: https://wiki.kaspa.org
- Developer docs: https://kaspa.org/build
- Official tooling streams block-added and DAA-change events

---

## QRL (Quantum Resistant Ledger)

Post-quantum PoW benchmark. Official explorer API directly exposes blocks, addresses, transactions, emission, reward, height, network status, mining stats via public JSON.

### Archive:
```text
height
difficulty
hashrate
reward
emission
tx_count
fees
xmss_address_count
ots_usage_distribution
address_activity
miner/pool
pool_share
```

### Future metric: post-quantum monetary-network premium
Compare QRL/QUAN against conventional PoW as quantum-related narratives/events happen.

### Data sources:
- Explorer API: https://docs.theqrl.org/api/explorer-api/
- Public gRPC API: https://docs.theqrl.org/api/qrl-public-api/
- Run own node recommended

---

## ZEPH (Zephyr Protocol)

Network with native stable asset and reserve mechanism. Already provides stable official historical API with reserve snapshots, APY history, pricing records.

### Archive every reserve snapshot:
```text
ZEPH_price
ZSD_supply
ZRS_supply
reserve_assets
reserve_ratio
oracle_price
block_reward
hashrate
mint/redemption activity
```

### Data sources:
- Official API: https://zephyrprotocol.com/documentation/scanner-api
- Endpoints: /api/v1/livestats, /api/v1/reservesnapshots, /api/v1/pricingrecords

---

## ALPH (Alephium)

Sharded PoW. Official public infrastructure exposes node API and explorer API with difficulty, hashrate, chain parameters, peer/network info.

### Archive:
```text
timestamp
shard
difficulty
hashrate
reward
emission
tx_count
fees
active_addresses
contracts
token activity
```

### Data sources:
- Public services: https://docs.alephium.org/infrastructure/public-services/

---

## ERG (Ergo)

Mature PoW, sophisticated UTXO programmability, miner governance. Supports dual mining with KAS/ALPH — useful for cross-chain capital/compute-flow models.

### Archive:
```text
difficulty
hashrate
reward
fees
storage_rent
pool_distribution
miner_voting
dex_liquidity
token_activity
```

### Data sources:
- Explorer API: https://docs.ergoplatform.com/dev/tutorials/blockchain-indexing/explorer-apis/
- Mining docs: https://docs.ergoplatform.com/mining/pools/

---

## XTM (Tari) — Already in SafeTrade, but add network data

Explorer exposes multiple simultaneous mining algorithms: RandomX, SHA3X, Cuckaroo29. Natural experiment for hardware allocation.

### Archive PoW split every minute/hour:
```text
timestamp
randomx_hashrate
sha3x_hashrate
cuckaroo29_hashrate
total_hashrate
block_time
reward
```

---

## Non-Chain Histories to Capture

### 1. Daily Hardware Prices
```text
date
gpu_model  # H100, H200, B200, RTX 4090, RTX 5090, etc.
price_usd
source
```

### 2. Electricity Prices
```text
date
country
region
tariff
currency
usd_per_kwh
```

### 3. Cloud GPU Prices
```text
date
provider  # Vast.ai, RunPod, Lambda, CoreWeave, Akash
gpu_model
hourly_usd
availability
```

### 4. Mining Software Performance
```text
miner_name
version
commit
hardware
algorithm
hashrate
power
stale_rate
rejected_rate
release_date
```

### 5. Pool Market Share
```text
chain
date
pool_name
share_pct
blocks_24h
```

### 6. GitHub/Release History
```text
repo
date
commit_sha
release_version
open_issues
commits_day
contributors
consensus_diff
miner_diff
tokenomics_diff
```

### 7. Narrative State
```text
date
youtube_video_count
youtube_views
reddit_mentions
x_mentions
google_trends
github_stars
discord_members
telegram_members
```

---

## Resource Market Framework

The cleanest version is not "crypto analytics." It's a telemetry layer for scarce machine resources. SafeTrade is just the first laboratory because it gives you lots of weird chains plus one venue where you already have L2.

The important expansion is to cover systems where the scarce thing differs:

* **QUBIC / PRL / TSC / GNK / NOCK** → compute / proof / useful-work markets
* **AKT** → decentralized GPU/CPU capacity market
* **PHA** → trusted execution / TEE capacity
* **LA** → proof-generation / verifiable-compute market
* **TAO** → intelligence/incentive markets
* **XMR / ZEPH / QRL / QUAN** → privacy, monetary security, post-quantum resilience

That lets Seesaw ask the same question everywhere:

> **What is scarce, what is paying for it, how quickly can supply respond, and what does the token capture?**

---

## AKT (Akash Network)

Decentralized GPU/CPU capacity market. Official API exposes provider-level real-time GPU inventory including GPU model and active/available/pending units. Providers compete for deployments on price and capacity.

### Archive every few minutes:

```text
akash_provider_snapshot
  timestamp
  provider
  online

  gpu_vendor
  gpu_model
  gpu_total
  gpu_active
  gpu_available
  gpu_pending

  cpu_total
  cpu_active
  memory_total
  storage_total

  region
  provider_attributes
```

### Derive:

```text
gpu_utilization
gpu_available_by_model
provider_concentration
capacity_growth
capacity_churn
```

### Archive bids / lease prices too:

```text
H100 $/hour
A100 $/hour
4090 $/hour
provider dispersion
capacity utilization
lease demand
```

This becomes a fundamental benchmark for PRL/Gonka/TSC/Qubic. If a protocol is paying the equivalent of $9/H100-hour in emissions while an H100 can rent for $2.50/hour on Akash, you immediately see the subsidy premium.

### Data sources:
- GPU Availability: https://akash.network/docs/api-documentation/rest-api/gpu-availability-guide/
- What is Akash: https://akash.network/docs/getting-started/what-is-akash/

---

## LA (Lagrange)

Market for **proof generation**. Combines ZK Prover Network, ZK Coprocessor and DeepProve zkML system. Prover network has 85+ institutional operators and uses marketplace architecture.

### Archive:

```text
lagrange_proof_job
  timestamp
  proof_system
  workload
  proving_time
  verification_time
  proof_size

  prover
  reward
  fee

  gpu_type
  hardware_count
```

### Derive:

```text
proofs/day
proofs/operator
USD/proof
USD/proving-second
proof_latency
verification_latency
operator_HHI
proof-demand-growth
```

### DeepProve:

```text
model
model_size
inference
proving_time
verification_time
proof_cost
```

### Data sources:
- Lagrange docs: https://docs.lagrange.dev/

---

## PHA (Phala Network)

Confidential cloud / TEE compute. Exposes Phala Cloud, Cloud API, proof/attestation infrastructure and hosted models.

### Archive:

```text
trusted_compute_snapshot
  timestamp
  network
  hardware_type
  tee_type          # TDX / SGX / etc

  nodes_online
  capacity
  utilization

  attestation_success_rate
  attestation_latency

  model
  inference_latency
  uptime
```

### Archive security incidents:

```text
security_event
  timestamp
  protocol
  severity
  layer_affected

  control_plane
  consensus
  tee
  wallet
  bridge

  systems_affected
  duration
  economic_loss
  remediation
```

### Data sources:
- Phala status: https://status.phala.network/
- P0 incident example: https://status.phala.network/incident/915228

---

## Universal Abstraction: Resource Markets

Organize the database around:

```text
RESOURCE
PROVIDER
DEMAND
PRICE
CAPACITY
UTILIZATION
SUBSIDY
TOKEN
PROOF
```

### Resource Market Table:

| Network    | Scarce resource                         |
| ---------- | --------------------------------------- |
| Akash      | GPU/CPU capacity                        |
| Gonka      | AI inference capacity                   |
| Pearl      | GPU mining/AI matrix work               |
| TensorCash | verified inference                      |
| Lagrange   | ZK proving                              |
| Phala      | attested confidential compute           |
| Nockchain  | proof generation / compute              |
| Qubic      | distributed computational work          |
| Bittensor  | specialized machine intelligence        |
| Monero     | censorship-resistant private settlement |

### Universal Snapshot:

```text
resource_market_snapshot
  timestamp

  network
  resource_type

  available_capacity
  utilized_capacity
  utilization_pct

  units_produced_24h
  units_consumed_24h

  market_price_per_unit

  protocol_subsidy_usd
  user_revenue_usd

  subsidy_per_unit
  external_market_price_per_unit

  provider_count
  provider_hhi
```

---

## Key Metrics

### Subsidy Dependence (SD)

$$
SD =
\frac{\text{token emissions paid to suppliers}}
{\text{token emissions + actual user payments}}
$$

| SD | Interpretation |
|----|----------------|
| 0.95 | 95% from inflation (bootstrapping) |
| 0.15 | Mostly real customers (mature) |

### Resource Coverage Ratio (RCR)

$$
RCR =
\frac{\text{market value of resource delivered}}
{\text{protocol subsidy}}
$$

| RCR | Interpretation |
|-----|----------------|
| 0.08 | Enormous overpayment |
| 0.80 | Healthy subsidy |

### Supply Elasticity

$$
E_s =
\frac{\%\Delta capacity}
{\%\Delta resource price}
$$

Track: `time_to_50pct_supply_response`

---

## Seesaw Quantified

### GPU example:
```text
new AI model → demand for H100 → H100 rental $/hr rises
→ Akash providers add H100s → utilization falls → price falls
```

### Pearl example:
```text
PRL rises → mining revenue/H100 rises → H100s enter
→ hashrate rises → miner issuance inventory rises → sell pressure rises
```

### Proving example:
```text
ZK demand rises → proof $/unit rises → provers add GPUs
→ proving capacity increases → latency/price fall
```

---

## External Data Sources to Add

| Network | Resource Type | Priority |
|---------|---------------|----------|
| **AKT** | GPU/CPU capacity | High |
| **PHA** | TEE compute | High |
| **LA** | ZK proving | High |
| **TAO** | Intelligence | High |
| **RunPod/Vast** | GPU rental (external control) | High |
