# PowPowPow

Continuously growing, provenance-preserving historical model of how computational resources are valued, allocated and transformed into economic output.

## Quick start

```bash
# venv
source /home/ubuntu/.venvs/powpowpow/bin/activate

# tests
python -m pytest tests/ -q

# check services
systemctl --user status pow-venue-l2 pow-chain-state pow-site

# refresh analytics
python scripts/qubic_analytics.py
python scripts/xmr_analytics.py

# rebuild daily state
python scripts/build_daily_state.py --date 2026-09-19

# compact warehouse
python scripts/compact_stream.py --all-seeds
```

## Live

Consumer site: https://pow.moltwork.com/?token=5tlDsoYg1Akp9e_0CAIUHzpLWwLEMfts

Token stored in systemd: `grep POW_SITE_TOKEN ~/.config/systemd/user/pow-site.service`

## What runs

- REST L2 collector: CoinEx + Gate + MEXC every 60s
- WebSocket tick archive: same venues
- Chain pollers: QUBIC RPC + XMR localmonero + KAS + Nockscan every 5min
- QUBIC epoch engine: burn schedule + net emission every 10min
- QUBIC computor snapshots + Doge tasks every hour
- Daily STATE + Parquet + trim at 00:30 UTC
- Consumer site behind Cloudflare tunnel on pow.moltwork.com

## V1 systems

PRL, QUBIC, QUAN, XMR, KAS, CLORE, AKT, NOS (defined in v1_registry.py)

## Key files

See HANDOVER.md for full map.

## Tests

```bash
python -m pytest tests/ -q
```

## Storage doctrine

- Hot JSONL: 7 days (trimmed)
- Parquet: forever (25-30x compressed)
- Raw: append-only forever (auto-archived)
- Chain bytes: extract-and-release (never hoarded)
- Everything else: derived tables kept forever (KBs)
- Off-box: R2 bucket `powpowpow-warehouse` (daily upload via `pow-r2-upload.timer`)
