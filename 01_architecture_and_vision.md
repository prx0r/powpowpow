# PowPowPow — Resources & Architecture Vision

Yes. I'd build **PowPowPow as a raw-data warehouse first and an API second**. The key is to preserve source-native data while normalizing enough fields that QUBIC, PRL, NOCK, QUAN, TSC, GNK and XMR can be compared and backtested together.

The architecture I'd use is:

**official chain/node → immutable raw events → normalized chain tables → SafeTrade L2/trades → derived metrics → backtests/API/content.**

Crucially, never discard the raw payload. These are young protocols and schemas will change.

## 1. Universal PowPowPow schema

Every observation should carry:

```text
source_observation
  observed_at
  chain_id
  source_id
  source_type          # rpc | websocket | grpc | explorer | git | exchange
  source_version
  endpoint
  request_params
  raw_payload
  payload_hash
  node_height
  node_tip_hash
  ingest_version
```

Then normalize into these core tables.

### `chain_snapshot`

```text
timestamp
chain
height
epoch
tip_hash

circulating_supply
max_supply
emitted_supply
burned_supply
locked_supply

difficulty
network_hashrate
target_block_time_s
realized_block_time_s

peer_count
active_nodes

tx_count_1h
tx_count_24h
fees_24h
mempool_tx_count
mempool_bytes
```

### `block`

```text
chain
height
hash
parent_hash
timestamp

difficulty
work
block_time_s

tx_count
fees_native
subsidy_native
miner_reward_native

miner_id
pool_id

proof_type
proof_metadata_json

canonical
orphaned
```

### `market_snapshot`

For your SafeTrade L2 data:

```text
timestamp
exchange
symbol
base
quote

best_bid
best_ask
mid
spread_bps

bid_depth_10bps
ask_depth_10bps
bid_depth_50bps
ask_depth_50bps
bid_depth_100bps
ask_depth_100bps
bid_depth_500bps
ask_depth_500bps

bid_notional
ask_notional
book_imbalance

microprice
```

And **store the individual levels separately**:

```text
orderbook_level
  timestamp
  market
  side
  price
  quantity
  level
  update_id
```

### `trade`

```text
timestamp
exchange
market
trade_id
price
quantity
notional_usd
aggressor_side
```

### `miner_economics`

```text
timestamp
chain

emission_native_day
emission_usd_day
fees_native_day
fees_usd_day

hashrate
difficulty

hardware_class
hashrate_per_device
power_w
electricity_usd_kwh

gross_revenue_day
electricity_cost_day
estimated_profit_day
profit_margin
payback_days
```

### `protocol_event`

This will become **massively useful** for backtests.

```text
timestamp
chain
event_type

height
epoch

old_value
new_value

source_commit
source_url
description
```

Examples: Qubic halving, new Aigarth workload, Nockchain protocol activation, Gonka model addition, Quantus difficulty-rule change, TSC Proof-v5 activation.

Then you can run event studies instead of just price indicators.

---

# 2. QUBIC — highest priority

Qubic has surprisingly good first-party infrastructure now.

### Authoritative sources

The main API is the official public RPC:

[Qubic RPC API documentation](https://docs.qubic.org/api/rpc/)

[Qubic public mainnet RPC](https://rpc.qubic.org/)

For example, the official docs specify `/v1/status`, `/v1/tick-info`, account balances and smart-contract queries. Qubic explicitly describes this RPC as suitable for production applications.

Use the official static registry for things the chain RPC doesn't conveniently label:

[Qubic static data registry](https://static.qubic.org/v1/general/data/)

It contains smart-contract metadata, exchange addresses, tokens, known address labels and protocol input types. That is particularly useful for identifying exchange movements.

Also retain:

[Official Qubic Explorer](https://explorer.qubic.org/)

[Official Qubic GitHub organization](https://github.com/qubic)

Qubic's own documentation specifically says balances, epoch, tick, computor set and contract state are directly queryable rather than requiring trust in a website.

### Qubic-specific schema

```text
qubic_tick
  tick
  timestamp
  epoch
  tx_count

qubic_epoch
  epoch
  start_tick
  end_tick
  start_timestamp
  end_timestamp

  gross_emission
  burned
  diverted
  net_emission

  active_computors
  mining_reward
  avg_solution_quality

qubic_computor
  epoch
  identity
  rank
  solutions
  reward
  status

qubic_contract_flow
  timestamp
  tick
  contract_index
  input_type
  sender
  amount
  decoded_action

qubic_balance
  timestamp
  identity
  balance
  label
```

### Metrics this unlocks

This is where Qubic gets interesting:

```text
net_issuance_usd_day
burn_ratio = burned / gross_emission
net_dilution_rate

qubic_emission_absorption =
    SafeTrade spot volume / net issuance USD

exchange_balance_delta
exchange_inflow_rate

epoch_return
return_since_epoch_start

hash/work proxy vs price
computor concentration
reward concentration

price / net_emission
FDV / net_emission
```

I'd also explicitly track **SafeTrade's known Qubic address balance** if Qubic's static labels expose it. That can eventually give you a quasi exchange-reserve series.

---

# 3. PEARL — possibly the best trading dataset

For PRL, I would **not make PearlTrack your canonical source**.

PearlTrack is excellent, but it states itself that it is an independent explorer. Use it for validation and labels.

Run `pearld` and query Pearl directly.

### Authoritative sources

[Official Pearl source repository](https://github.com/pearl-research-labs/pearl)

[Official pearld JSON-RPC specification](https://github.com/pearl-research-labs/pearl/blob/master/node/docs/json_rpc_api.md)

Pearl's daemon supports HTTP JSON-RPC and WebSockets; the latter can provide asynchronous notifications.

For wallet-level data:

[Official Pearl wallet gRPC specification](https://github.com/pearl-research-labs/pearl/blob/master/wallet/rpc/documentation/api.md)

And use this as your secondary analytics/label layer:

[PearlTrack public API](https://www.pearltrack.io/api)

Base API path is `/api/v1`. It provides address histories, identified mining pools and change-adjusted large transfers.

### Pearl-specific schema

This needs to be much richer because **miner flows are the trade thesis**.

```text
prl_block
  height
  timestamp
  difficulty
  reward
  miner_address
  pool
  tx_count
  fees

prl_pool
  timestamp
  pool
  blocks_24h
  share_24h
  rewards_24h

prl_miner_flow
  timestamp
  txid

  source_pool
  miner_address
  destination

  amount_prl

  classification:
    pool_payout
    miner_transfer
    consolidation
    suspected_exchange_deposit

prl_address
  address
  first_seen
  last_seen
  balance
  received
  sent

  label
  label_confidence
  pool_name
  suspected_exchange
```

You can use PearlTrack's `poolPayout`, `distribution`, `transfer` and `consolidation` classifications as **secondary evidence**, not canonical truth. Its API also explicitly change-adjusts transfers, which is useful.

### Killer PRL metrics

```text
miner_emission_usd_day

miner_realization_ratio =
    estimated miner outbound PRL /
    newly emitted PRL

pool_to_exchange_prl_24h

pool_to_exchange_usd_24h

sell_pressure_ratio =
    estimated miner exchange inflow /
    SafeTrade bid depth within 5%

absorption_ratio =
    aggressive buys /
    miner-originated sell volume

hashrate_price_elasticity

difficulty_price_lag

miner_profit_margin

miner_profitability_zscore
```

**This is what I'd use to attack the Pearl question we were discussing.**

Instead of saying "PRL has huge miner sell pressure," PowPowPow could eventually say:

> PRL miners received $942k over 24h, approximately $481k moved out of identified pool payout clusters, SafeTrade bid depth within 5% is $X, and absorption has declined 37% in 72h.

That's tradable information.

---

# 4. Nockchain / NOCK

Nockchain is particularly worth archiving **now**, because the protocol is evolving rapidly.

### Authoritative sources

Start with Nockchain's own trust hierarchy:

[Nockchain START_HERE](https://github.com/nockchain/nockchain/blob/master/START_HERE.md)

[Canonical Nockchain protocol index](https://github.com/nockchain/nockchain/blob/master/PROTOCOL.md)

The maintainers explicitly designate these as their canonical protocol sources and version protocol changes through activation specifications.

For machine data:

[Nockchain public API documentation](https://github.com/nockchain/nockchain/blob/master/crates/nockchain-api/README.md)

Run **your own `nockchain-api` node**.

It exposes `NockchainService` and `NockchainBlockService` over gRPC, including block-explorer queries such as `GetBlocks`, `GetTransactionBlock` and `GetTransactionDetails`. The maintainers explicitly warn that this API is currently alpha and operator-managed.

### NOCK schema

```text
nock_block
  height
  hash
  timestamp

  difficulty
  proof_type
  proof_size_bytes
  proof_generation_metadata

  miner
  reward
  tx_count

nock_protocol_version
  height
  version
  activation_name
  activation_spec

nock_proof
  block_height
  proof_type
  proof_size
  proving_time
  verification_time

nock_compute_work
  timestamp
  block
  work_type
  workload_id
  useful_work_units
  proof_status
```

### Especially interesting metrics

```text
proof_bytes_per_block
verification_cost_per_block
proof_generation_latency

NOCK emitted / proof produced

USD miner subsidy /
verified computation

protocol-upgrade event returns

difficulty response to price

proof throughput
```

When useful-compute functionality matures, this table becomes incredibly valuable because you can compare **economic subsidy per unit of verifiable computation** with Qubic/TSC/Gonka.

---

# 5. Quantus / QUAN

One warning: some current Quantus developer documentation still uses **QTC** internally, while SafeTrade's official September 9 listing identifies the market asset as **QUAN**. Don't use symbol as your primary database key—use something like `quantus-mainnet`; symbols are presentation metadata.

### Official resources

[Quantus technical documentation](https://docs.quantus.com/)

[Quantus QPoW specification](https://docs.quantus.com/deep-dives/qpow/)

[Quantus Explorer](https://explorer.quantus.com/)

[Quantus telemetry dashboard](https://telemetry.quantus.cat/)

Most useful for us:

[Quantus Subsquid GraphQL endpoint](https://sub2.quantus.com/v1/graphql)

The official Quantus CLI currently uses that as its default Subsquid indexer endpoint.

And:

[Quantus core chain repository](https://github.com/Quantus-Network/chain)

[Quantus miner source](https://github.com/Quantus-Network/quantus-miner)

The emission rule is particularly useful because it is deterministic:

`block_reward = (max_supply - current_supply) / emission_divisor`

with the current mainnet divisor documented as **50,000,000**.

### QUAN schema

```text
quantus_block
quantus_reward
quantus_account

quantus_wormhole_transfer
  block
  timestamp
  commitment
  amount
  claimed
  claim_height

quantus_miner
  miner_id
  reward_inner_hash
  wormhole_address

quantus_network
  timestamp
  nodes
  peers
  difficulty
  block_time
```

And critically:

```text
quantus_vesting
  allocation_id
  allocation_type
  original_amount
  unlocked_amount
  locked_amount
  next_unlock
```

Why? Quantus has both miner issuance **and genesis vesting**, so circulating-supply pressure isn't just mining. Official docs describe a 27% genesis allocation and 73% mining allocation.

### Metrics

```text
miner_issuance_day
vesting_unlock_day
total_new_liquid_supply_day

miner_supply_pressure
investor_supply_pressure

wormhole_usage
private_tx_fraction

node_count
miner_concentration

quantum_security adoption proxies
```

---

# 6. TensorCash / TSC

TensorCash is almost designed for PowPowPow.

Its observability stack is excellent.

### Official resources

[TensorCash complete developer docs](https://tensorcash.org/docs/)

[TensorCash JSON-RPC reference](https://tensorcash.org/docs/rpc/)

[TensorCash core-node REST API](https://tensorcash.org/docs/core-node/api/)

[TensorCash verifier API](https://tensorcash.org/docs/verifier/api/)

[TensorCash ZMQ event specification](https://tensorcash.org/docs/zmq/)

[TensorCash proof schemas](https://tensorcash.org/docs/schemas/)

The RPC includes normal Bitcoin-derived data plus TensorCash-specific operations, including `getminingworkunitinfo`.

The verifier exposes a whole verification ladder including `full`, `model`, `pow`, `quick`, `quick-smell` and `logits` verification.

### TSC-specific schema

```text
tsc_work_unit
  work_id
  timestamp

  model_id
  model_version

  inference_type
  input_tokens
  output_tokens

  gpu_type
  runtime_ms

  proof_hash
  proof_type
  proof_bytes

  verification_level
  verification_latency_ms
  verification_result

  miner
  reward_tsc
```

Also:

```text
tsc_model
  model_id
  registered_at
  active
  architecture
  parameters
  quantization

tsc_verification
  timestamp
  work_id
  verifier
  verification_mode
  valid
  latency
```

### This gives exceptional metrics

```text
verified_inferences/day
verified_tokens/day

miner_reward_per_inference
miner_reward_per_1M_tokens

USD subsidy / 1M verified tokens

invalid_proof_rate
verification_latency

useful_compute_utilization

GPU revenue/hour
GPU revenue/watt

TSC market cap /
daily verified inference
```

That last family is exactly the kind of **fundamental valuation primitive that doesn't currently exist on CoinGecko.**

---

# 7. Gonka / GNK

Gonka may have the richest actual compute-side dataset.

### Official live endpoints

Use their public nodes.

[Gonka current epoch participants](https://node2.gonka.ai:8443/v1/epochs/current/participants)

This exposes host identity, voting weight, inference endpoint, supported models, epoch information, validators and proofs.

Protocol/inference parameters:

[Gonka live inference parameters](https://node3.gonka.ai/chain-api/productscience/inference/inference/params)

This is particularly valuable because Gonka's own docs tell operators to **read parameters live from chain instead of assuming static values**.

Docs:

[Gonka Network Node API docs](https://gonka.ai/docs/host/network-node-api/)

[Official Gonka repository](https://github.com/gonka-ai/gonka)

And this first-party tracker implementation is basically a blueprint for your collector:

[Gonka inference tracker source](https://github.com/gonka-ai/gonka-tracker)

It already computes inference counts, missed rates, invalidation rates, node health, jail status, weights and models.

### Gonka schema

```text
gonka_epoch
  epoch
  poc_start_height
  start_height
  end_height

gonka_host
  epoch
  address
  validator_key

  weight
  inference_url

  jailed
  healthy

gonka_host_model
  epoch
  host
  model_id

gonka_inference
  epoch
  host
  model

  attempted
  successful
  invalidated
  missed

gonka_model_params
  timestamp
  model_id

  weight_scale_factor
  penalty_start_epoch

gonka_reward
  epoch
  host
  reward
```

### Metrics

```text
network_compute_weight

host_market_share
compute_concentration_HHI

successful_inference_rate
miss_rate
invalidation_rate

model_mix

reward_per_weight
reward_per_successful_inference

GNK issuance /
successful inference

model activation event returns

GPU profitability by hardware

host churn
```

You could eventually detect things such as:

> DeepSeek V4 was added → network GPU composition changed → useful inference increased 28% → GNK price didn't move.

That's exactly the sort of information market participants won't have cleanly organized.

---

# 8. Monero / XMR

XMR should be the **control group**.

It's mature PoW and doesn't pretend the computation itself is valuable. That makes it very useful when comparing security expenditure against "useful PoW."

### Canonical resources

[Current Monero daemon RPC documentation](https://docs.getmonero.org/rpc-library/monerod-rpc/)

[Official Monero source repository](https://github.com/monero-project/monero)

Run your own `monerod`; don't base this dataset on an explorer.

Important calls include:

```text
get_info
get_block_header_by_height
get_block_headers_range
get_block
get_coinbase_tx_sum
get_miner_data
get_fee_estimate
get_transaction_pool
get_transaction_pool_stats
get_connections
```

`get_coinbase_tx_sum` gives you emission and fees over arbitrary block windows, while `get_miner_data` exposes network difficulty, current height, generated supply and mineable mempool data.

### XMR schema

```text
xmr_block
  height
  timestamp
  difficulty
  reward
  fees
  weight
  tx_count

xmr_network
  timestamp
  difficulty
  estimated_hashrate
  mempool
  peers

xmr_emission
  timestamp
  emission
  fees
  generated_supply
```

You **cannot do PRL-style address-flow analytics with XMR** by design. That's not a data deficiency; it's part of what you're measuring.

Interesting metrics:

```text
security_budget_usd
fees / miner_revenue

hashprice
revenue_per_hash

difficulty response to XMR price

mempool pressure
fee pressure

USD security spend /
transaction

XMR security-cost benchmark
```

Then compare:

```text
QUBIC subsidy / useful work
TSC subsidy / inference
GNK subsidy / inference
PRL subsidy / claimed useful work
NOCK subsidy / proof work

vs

XMR subsidy / pure consensus security
```

That comparison itself could become excellent content.

---

# 9. The SafeTrade dataset is what makes all of this tradable

Since you already have **full L2**, archive it at the highest resolution you reasonably can.

Don't just save candles.

Store:

```text
raw book updates
raw trades
periodic full-book checkpoints
```

Then derive 1s / 10s / 1m / 5m bars for:

```text
mid_return
spread_bps

depth ±10bps
depth ±25bps
depth ±50bps
depth ±100bps
depth ±500bps

book_imbalance

aggressive_buy_usd
aggressive_sell_usd

trade_imbalance

cancel_rate_bid
cancel_rate_ask

depth_added_bid
depth_added_ask

realized_slippage_$100
realized_slippage_$1k
realized_slippage_$10k
```

---

# 10. The really valuable cross-chain table

This becomes your **PowPowPow factor table**:

| Factor                      | Meaning                                      |
| --------------------------- | -------------------------------------------- |
| `issuance_usd_24h`          | New native supply valued at spot             |
| `issuance_to_mcap`          | Dilution pressure                            |
| `issuance_to_volume`        | How large emission is versus turnover        |
| `issuance_to_bid_depth`     | Immediate absorption burden                  |
| `miner_profit_margin`       | Incentive to add compute                     |
| `hashrate_growth`           | Supply response                              |
| `price_hashrate_divergence` | Potential miner capitulation/euphoria        |
| `miner_to_exchange_flow`    | Observable structural selling where possible |
| `compute_units`             | Actual useful work                           |
| `subsidy_per_compute`       | Cost paid by token holders per useful unit   |
| `compute_growth`            | Fundamental demand/output growth             |
| `book_imbalance`            | Short-term liquidity pressure                |
| `aggressive_flow`           | Actual marginal buyer/seller direction       |
| `protocol_event`            | Causal catalyst                              |
| `developer_activity`        | Build trajectory                             |

And then create factors such as:

```text
ABSORPTION_PRESSURE =
    issuance_usd_24h /
    bid_depth_5pct
```

```text
MINER_STRESS =
    electricity_cost /
    gross_mining_revenue
```

```text
COMPUTE_EFFICIENCY =
    external_value_of_compute /
    miner_subsidy_usd
```

```text
FUNDAMENTAL_MOMENTUM =
    Δ useful_compute /
    Δ market_cap
```

```text
REFLEXIVITY =
    corr(
      price_change,
      hashrate_change_lagged,
      issuance_value_change,
      speculative_volume_change
    )
```

That last one should be fascinating for **Pearl**.

## My ingestion order

I wouldn't try to build all seven adapters simultaneously.

**Phase 1: QUBIC + PRL + SafeTrade L2.**

Those alone let you test two radically different emission/mining regimes against the same exchange.

**Phase 2: TSC + GNK.**

Now you have genuinely measurable AI/useful-compute output.

**Phase 3: NOCK + QUAN.**

Add ZK/proof-native and post-quantum systems.

**Phase 4: XMR.**

Use it as the mature PoW/control benchmark and later connect the mining/profitability side to XMRBot.

If you get the **canonical schema right first**, adding TAO, QRL, ZEC, Bittensor subnets, Qubitcoin, new SafeTrade launches, etc. becomes an adapter problem rather than another project.

And I think the killer PowPowPow API eventually isn't `/price/QUBIC`.

It's something more like:

```text
/chains/QUBIC/fundamentals
/chains/PRL/miner-pressure
/chains/TSC/compute
/chains/GNK/models
/chains/XMR/security-budget

/markets/PRL-USDT/absorption
/mining/profitability
/factors
/events
/backtests
```

That is a legitimately interesting data product because it answers questions existing crypto APIs mostly don't even model.

---

# Additional Resources Found During Research

## Chain Explorers & APIs

### QUBIC
- Official Explorer: https://explorer.qubic.org
- QLI Network Stats: https://app.qubic.li
- QLI Analytics: https://analytics.qubic.li
- Qubic RPC: https://rpc.qubic.org
- Qubic Static Data: https://static.qubic.org/v1/general/data/
- DOGE Mining Stats: https://doge-stats.qubic.org

### PRL (Pearl)
- PRLScan: https://prlscan.com (hashrate: 21.9 EH/s, difficulty: 19.99M)
- PearlTrack: https://pearltrack.io
- PearlTrack API: https://pearltrack.io/api/v1
- PearlPool: https://pearlpool.cloud
- PearlPool.io: https://pearlpool.io

### NOCK (Nockchain)
- NockBlocks Explorer: https://nockblocks.com (has API)
- NockScan: https://nockscan.net (has API at /api/v1)
- NockScan API endpoints: /api/v1/recent-blocks, /api/v1/block/{id}, /api/v1/holders, /api/v1/proof-rate, /api/v1/block-time-stats

### XMR (Monero)
- XMRChain: https://xmrchain.net
- P2Pool Observer: https://p2pool.observer
- Minero API: https://minero.cc/api/network
- CoinWarz: https://api.coinwarz.com/v1/metrics?coin=xmr
- Network hashrate: ~5.6 GH/s
- Difficulty: ~691B
- Block reward: 0.6 XMR (tail emission)

### GNK (Gonka)
- Gonka.gg Explorer: https://gonka.gg (has API, 50k req/day)
- GonkaLab Explorer: https://gonkalab.ai
- GNKScan: https://gnkscan.com
- Gonka RPC: https://rpc.gonka.gg
- Gonka Proxy (OpenAI-compatible): https://proxy.gonka.gg
- OpenBroker: https://openbroker.gonka.gg
- Gonka Tracker (reference implementation): https://github.com/gonka-ai/gonka-tracker
- Status Dashboard: https://power.gnk.space
- Current stats: 734 GPUs, 29 ML nodes, 2,303 H100 equivalents

### TSC (TensorCash)
- Docs: https://tensorcash.org/docs/
- JSON-RPC: https://tensorcash.org/docs/rpc/
- Core-node REST: https://tensorcash.org/docs/core-node/api/
- Verifier API: https://tensorcash.org/docs/verifier/api/
- ZMQ Events: https://tensorcash.org/docs/zmq/
- Git: https://git.tensorcash.org/tensorcash

### XEL (Xelis)
- Explorer: https://explorer.xelis.io
- Stats: https://stats.xelis.io
- Network hashrate: 49.49 MH/s
- Difficulty: 248.28M
- Block time: 5s
- Max supply: 18.4M
- Dev fee: 5%

### XTM (Tari)
- Explorer: https://explore.tari.com
- RandomX hashrate: 3.6 GH/s
- Sha3X hashrate: 380.2 TH/s
- Block reward: ~10,930 XTM
- Kryptex pool: 7.44 MH/s, 1440 miners
- Merge mined with Monero

### QTC (Qubitcoin)
- Explorer: https://explorer.superquantum.io
- LuckyPool: 81.6% hashrate (centralization risk)
- Network hashrate: 18.29 TH/s
- Block time: 675s
- Max supply: 2.31M

## Mining Profitability Data (from Kryptex)

### RTX 4080 Super Daily Revenue
| Coin | Hashrate | Revenue | Profit |
|------|----------|---------|--------|
| PRL | 203 TH/s | $1,954 | $1,859 |
| QTC | 755 MH/s | $1,639 | $1,568 |
| XEL | 10.1 KH/s | $100 | $50 |
| XTM | 12.3 H/s | $122 | $60 |

### CMP 170HX Daily Revenue
| Coin | Hashrate | Revenue | Profit |
|------|----------|---------|--------|
| PRL | 175 TH/s | $752 | $667 |
| XEL | 20.8 KH/s | $157 | $101 |

## GitHub Repositories

| Coin | Repository | Stars | Language |
|------|------------|-------|----------|
| QUBIC | qubic/core | 187 | C++ |
| PRL | pearl-research-labs/pearl | 304 | Rust |
| NOCK | nockchain/nockchain | 494 | Rust |
| XMR | monero-project/monero | 10,859 | C++ |
| GNK | gonka-ai/gonka | 629 | Go |
| TSC | tensorcash/tensorcash | - | Python |
| XEL | xelis-project/xelis-blockchain | 439 | Rust |
| XTM | tari-project/tari | 499 | Rust |

## Community Links

| Coin | Discord | Twitter | GitHub |
|------|---------|---------|--------|
| QUBIC | discord.gg/qubic | @QubicNetwork | github.com/qubic |
| PRL | discord.gg/pearl | @PearlResearch | github.com/pearl-research-labs |
| NOCK | discord.gg/nockchain | @Nockchain | github.com/nockchain |
| XMR | #monero-dev (Libera IRC) | @monero | github.com/monero-project |
| GNK | discord.gg/gonka | @gonka_gg | github.com/gonka-ai |
| TSC | - | - | github.com/tensorcash |
| XEL | discord.gg/xelis | - | github.com/xelis-project |
| XTM | discord.gg/tari | @tari_project | github.com/tari-project |

## Key API Endpoints for Data Collection

```text
# Qubic
GET https://rpc.qubic.org/v1/status
GET https://rpc.qubic.org/v1/tick-info
GET https://static.qubic.org/v1/general/data/

# Pearl
GET https://pearltrack.io/api/v1/blocks
GET https://pearltrack.io/api/v1/pools
POST https://rpc.pearlresearch.ai (JSON-RPC)

# Nockchain
GET https://nockscan.net/api/v1/recent-blocks
GET https://nockscan.net/api/v1/block/{id}
GET https://nockscan.net/api/v1/holders
GET https://nockscan.net/api/v1/proof-rate

# Monero
POST https://rpc.monero.obl.alee.pw/json_rpc
  method: get_info
  method: get_coinbase_tx_sum
  method: get_miner_data

# Gonka
GET https://node2.gonka.ai:8443/v1/epochs/current/participants
GET https://node3.gonka.ai/chain-api/productscience/inference/inference/params
GET https://rpc.gonka.gg/cosmos/bank/v1beta1/supply

# Xelis
GET http://127.0.0.1:8080/get_blocks_by_range
GET http://127.0.0.1:8080/get_network_info

# Tari
GET https://explore.tari.com/api/blocks
grpc://127.0.0.1:18142 (Minotari gRPC)

# Quantus
POST https://sub2.quantus.com/v1/graphql (Subsquid)
GET https://explorer.quantus.com/api/blocks
```
