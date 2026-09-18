# PowPowPow

**A point-in-time dataset of decentralized compute, proof, privacy and machine-resource markets.**

## The Seesaw Filter

> **No machine-readable supplier/miner telemetry → no core dataset.**

We only track systems where we can measure:
- Who supplies the scarce resource
- How much they supply
- What they earn
- How that changes over time

## Canonical Universe V1 — 16 Systems

### Compute / Useful Work
| Coin | Resource | Supplier |
|------|----------|----------|
| QUBIC | CPU computation | Computors |
| PRL | H100 GPU work | Miners |
| NOCK | ZK proof generation | Provers |
| QUAN | Post-quantum PoW | Miners |
| TSC | Verified AI inference | Miners |
| GNK | AI inference capacity | Hosts |
| TIG | Algorithmic efficiency | Benchmarkers |
| TAO | Machine intelligence | Miners/Validators |

### Resource Markets
| Coin | Resource | Supplier |
|------|----------|----------|
| AKT | GPU/CPU capacity | Providers |
| CLORE | GPU marketplace | Providers |
| NOS | GPU compute | Hosts |
| TFUEL | GPU jobs + inference | Edge nodes |
| FLUX | Compute nodes + PoW | Nodes |

### PoW / Privacy / Security
| Coin | Resource | Supplier |
|------|----------|----------|
| XMR | CPU mining security | Miners |
| QRL | XMSS signatures | Miners |
| MCM | WOTS+ GPU PoW | Miners |

### Control
| Coin | Resource | Supplier |
|------|----------|----------|
| KAS | High-throughput PoW | Miners |

## Repository Structure

```
powpowpow/
├── README.md                           # This file
├── 01_architecture_and_vision.md       # System design
├── 02_pressure_equation_research.md    # Academic research
├── 03_seesaw_filter.md                 # Inclusion criteria
├── 04_canonical_universe_v1.md         # 16 core systems
├── 05_extended_coin_research.md        # Additional research
├── 06_moat_strategy.md                 # Competitive moat
├── 07_coin_categories.md               # Category definitions
├── canonical.md                        # Canonical universe V1
├── tier2.md                            # Secondary systems
│
├── registry.py                         # Coin registry
├── categories.py                       # Category system
├── schema.py                           # Universal data schema
├── warehouse.py                        # Raw event storage
│
├── api.py                              # REST API
├── daemon.py                           # Master daemon
├── pressure.py                         # Pressure equation
├── ofi.py                              # Order Flow Imbalance
├── two_timescale.py                    # Structural + trigger model
│
├── collectors/                         # Data collectors
│   ├── qubic_collector.py
│   ├── prl_collector.py
│   ├── nock_collector.py (planned)
│   ├── quan_collector.py (planned)
│   ├── tsc_collector.py (planned)
│   ├── gnk_collector.py (planned)
│   ├── tig_collector.py
│   ├── tao_collector.py
│   ├── akt_collector.py
│   ├── clore_collector.py
│   ├── nos_collector.py
│   ├── theta_collector.py
│   ├── flux_collector.py
│   ├── xmr_collector.py (planned)
│   ├── qrl_collector.py
│   ├── mcm_collector.py
│   ├── kas_collector.py (planned)
│   └── l2_archival.py
│
├── chains/                             # Per-chain data
│   ├── QUBIC/
│   ├── PRL/
│   ├── NOCK/
│   ├── QUAN/
│   ├── TSC/
│   ├── GNK/
│   ├── TIG/
│   ├── TAO/
│   ├── AKT/
│   ├── CLORE/
│   ├── NOS/
│   ├── THETA/
│   ├── FLUX/
│   ├── XMR/
│   ├── QRL/
│   ├── MCM/
│   └── KAS/
│
├── warehouse/                          # Raw + normalized data
├── historical_data/                    # Price history, OHLCV
├── exports/                            # Backtest data
└── docs/                               # Documentation
```

## Quick Start

```bash
# Start daemon
python3 daemon.py

# Run collectors
python3 collectors/clore_collector.py
python3 collectors/theta_collector.py

# Get pressure metrics
python3 pressure.py

# Export backtest data
python3 export.py
```

## Key Metrics

### Resource Premium
```
protocol reward per unit resource / external market price per unit resource
```

### Supply Elasticity
```
%Δ resource capacity / %Δ resource profitability
```

### Subsidy Dependence
```
token emissions paid to suppliers / (token emissions + user payments)
```
