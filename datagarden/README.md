# Data Garden Primitives for PowPowPow

This directory contains the shared Data Garden framework used by both UKBoring and PowPowPow.

## What's Here

### core/ — The Universal Primitives

These are garden-agnostic. They define the vocabulary every Data Garden speaks:

- `observation.py` — The atom. Immutable record from reality with deterministic SHA-256 ID. TruthClass (VERIFIED/DERIVED/ESTIMATED/HEURISTIC/CONCEPTUAL/UNAVAILABLE). Recoverability (CANONICAL/THIRD_PARTY/PARTIAL/EPHEMERAL).
- `entity.py` — Permanent thing observed over time. Lifecycle: active → superseded → dead. Name history, first_seen/last_seen.
- `source.py` — Data source metadata. Cadence, reliability, terms, freshness SLA.
- `derived.py` — Computed fact with provenance chain. Method version, input observation IDs, confidence, validity window.
- `quality.py` — QualityState (KNOWN/INFERRED/STALE/CONFLICTED/UNKNOWN). QualityGate validates before storage.
- `storage.py` — Append-only JSONL, thread-safe, date-partitioned.
- `capability.py` — CapabilityResult contract. Truth class, confidence, evidence, action class.
- `outcome.py` — Feedback loop primitive. Predicted vs actual, user satisfaction.
- `receipt.py` — Evidence that outcome occurred. Actuality (TRUE/FALSE/UNKNOWN), proof rules.
- `signal.py` — Detected change in economic graph.
- `hardware.py` — Mining profitability observation for hardware on network.
- `valuation.py` — Full evidence chain for physical item valuation.

### shared/ — Infrastructure + PowPowPow-Specific

- `warehouse.py` — Two-tier storage: canonical_backfill (reconstructable) vs ephemeral_archive (time-sensitive). Already configured for powpowpow chains (qubic, prl, nock, xmr, gnk, kas).
- `manifest.py` — Daily Merkle manifests. SHA-256 Merkle tree over all warehouse files. Cryptographic proof of data existence.
- `schema.py` — ALL powpowpow domain types: ChainConfig, NetworkStats, EmissionData, MinerData, MarketData, OrderBookData, MiningPoolSnapshot, StratumJob, GPUAvailability, PowerMarket, ExchangeTick, ASICQuote.
- `entities.py` — Permanent entity registry. Bootstrapped with powpowpow networks, assets, exchanges, hardware.
- `normalize.py` — Unified normalization dispatch. Routes to powpowpow. JSONL helpers.
- `jev.py` — LLM-based observation classification. Has POWPOWPOW_OBSERVATION_QUESTIONS for mining/economics signals.
- `experiment.py` — Experiment tracking for content generation.

### Conceptual Documents

- `thesis.md` — The founding document. Section 7 is literally "PowPowPow as the canonical example."
- `formula.md` — Moat theory, loop mechanics, audience-as-data.
- `ideology.md` — "Consumed worlds," accumulated resolution, ME (production economics).
- `architecture.md` — UK-Boring-specific but useful for QP-lite concepts (Receipt, Actuality, Evidence, Gate).

## How PowPowPow Uses This

PowPowPow is a first-class Data Garden. It was co-designed alongside UKBoring from the beginning.

The key primitives PowPowPow uses:
- **Observation** → Every stratum job, pool state, exchange tick, emission event
- **Entity** → Networks, pools, exchanges, hardware (all in shared/entities.py)
- **DerivedFact** → Seesaw state, profitability calculations, miner margin estimates
- **Source** → SafeTrade WS, Qubic RPC, Electricity Maps, CoinGecko API
- **QualityGate** → Validate data before storage (STALE for stratum data, KNOWN for monthly emissions)
- **Receipt** → Settlement proofs ("did this block actually get found?")
- **Warehouse** → Two-tier storage (canonical for backfill, ephemeral for live data)
- **Manifest** → Cryptographic proof that September 2026 mining data existed in September 2026

## Files NOT Copied (UK-Boring-Specific)

These are in datagarden but NOT useful for PowPowPow:
- `core/workflow.py` — UK administrative tasks
- `core/capability_envelope.py` — Human person context (skills, GBP capital)
- `core/route.py` — RouteType enums (JOB, GIG, GRANT)
- `core/decision_spec.py` — UK-Boring predefined specs

## Data Flow

```
Collectors → Observations → QualityGate → Canonical Store
                                            ↓
                                    Derived Facts (profitability, seesaw)
                                            ↓
                                    MCP Tools → Muse/Agents
                                            ↓
                                    Receipts → Outcome Tracking
                                            ↓
                                    Manifests → Cryptographic Proof
```

## Notes

- The `core/` package is garden-agnostic. PowPowPow sets `garden="powpowpow"` on every Observation.
- The `shared/` package already has powpowpow-specific config (warehouse subdirs, entity bootstrap, schema types).
- `shared/jev.py` has mining-specific Jev questions (difficulty changes, hashrate shifts, pool migrations).
- All files are MIT licensed. Use freely.
