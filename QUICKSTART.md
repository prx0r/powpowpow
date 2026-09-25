> **STALE 2026-09-25 — every command in this file is wrong for this box.**
> Venv `/home/ubuntu/.venvs/powpowpow` and repo `/home/ubuntu/powpowpow` do
> not exist (real path `/root/powpowpow`); `pow-venue-l2.service` is
> not-found; SafeTrade is unblocked and running as `pow-safetrade-l2`, not
> geo-blocked; the API entry point is `pow-site.service`, not `api/app.py:5000`.
> Current truth: `docs/pow-systems-live.md`.

# PowPowPow — Quick Start

Venv: `/home/ubuntu/.venvs/powpowpow` (has `websockets`, `requests`).
Repo: `/home/ubuntu/powpowpow`. All paths repo-relative — no `/home/box`.

## 1. Venue L2 collector (systemd, autonomous)

```bash
systemctl --user status pow-venue-l2.service
systemctl --user restart pow-venue-l2.service
journalctl --user -u pow-venue-l2.service -n 30
cat warehouse/venue_l2_heartbeat.json
```

Single test pass instead of the daemon loop:

```bash
/home/ubuntu/.venvs/powpowpow/bin/python collectors/venue_l2.py --once
```

## 2. SafeTrade L2 collector (staged — needs unblocked egress)

```bash
/home/ubuntu/.venvs/powpowpow/bin/python collectors/l2_archival.py --once 60
```

SafeTrade REST + WS return HTTP 403 from this box (geo-block, verified
direct and via agent-vault proxy). Run the above from any unblocked
machine and rsync `warehouse/` back, or point it at a proxy on
unblocked egress.

## 3. Daily STATE rollup

```bash
/home/ubuntu/.venvs/powpowpow/bin/python scripts/build_daily_state.py --date 2026-09-19
```

## 4. Start API

```bash
cd /home/ubuntu/powpowpow/api
/home/ubuntu/.venvs/powpowpow/bin/python app.py
```

Reads latest orderbook snapshots from `warehouse/normalized`
(falls back to `SAFETRADE_TRACKED_DIR` flat files if set).

## 5. Money math / live cards

```bash
/home/ubuntu/.venvs/powpowpow/bin/python v1_live_cards.py
/home/ubuntu/.venvs/powpowpow/bin/python economics.py
```

Network-share revenue model. KAS gated until emission + hashrate measured.

## 6. Export backtest data

```bash
/home/ubuntu/.venvs/powpowpow/bin/python export.py
```

OHLCV falls back to warehouse `daily_state` mid-OHLC when no
`SAFETRADE_TRACKED_DIR` is set.

## Retired (old /home/box machine, not on this VPS)

`safetrade/daemon.py`, `feature_pipeline.py`, `train_model.py`,
`live_predictions.py` — the old tracker + ML pipeline were never migrated.
Replacements: `collectors/venue_l2.py` (collection),
`scripts/build_daily_state.py` (state), `export.py` (backtest sets).
