# systemd units

The 23 `pow-*` unit/timer files here are the committed source of truth.
Live copies live in `~/.config/systemd/user/` — they must be identical
(check: `diff -rq ~/.config/systemd/user systemd --exclude=default.target.wants
--exclude=timers.target.wants --exclude=hermes-gateway-patala.service`).

> **Paths are absolute:** every unit hardcodes `WorkingDirectory=/root/powpowpow`
> and `/usr/bin/python3`. On a different box, edit `WorkingDirectory`,
> `ExecStart` paths and `ReadWritePaths` before installing.

## Install

```bash
cd /root/powpowpow
cp systemd/pow-*.service systemd/pow-*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
```

## Enable

Always-on services (`Restart=always`):

```bash
systemctl --user enable --now \
  pow-safetrade-l2.service pow-chain-state.service \
  pow-qubic-stats.service pow-qubic-holdings.service pow-qubic-transfers.service \
  pow-site.service pow-cloudflared.service
```

Timers:

```bash
systemctl --user enable --now \
  pow-health.timer pow-daily-state.timer pow-qubic-epoch.timer \
  pow-qubic-computors.timer pow-mining-analytics.timer \
  pow-r2-upload.timer pow-r2-retention.timer pow-warehouse-compact.timer
```

Confirm the box survives logout (`Linger=yes` is already set):

```bash
loginctl show-user root -p Linger
systemctl --user list-units 'pow-*' --state=running
systemctl --user list-timers 'pow-*' --no-pager
```

## Inventory

| Unit | Kind | Schedule |
|---|---|---|
| `pow-safetrade-l2` | service | continuous, SafeTrade WS depth/trades/tickers |
| `pow-chain-state` | service | continuous, QUBIC/XMR/BTC every 300s |
| `pow-qubic-stats` | service | continuous, official stats every 300s |
| `pow-qubic-holdings` | service | continuous, exchange reserves + rich list every 6h |
| `pow-qubic-transfers` | service | continuous, transfer windows every 300s |
| `pow-site` | service | dashboard origin, loopback :8795 |
| `pow-cloudflared` | service | tunnel daemon |
| `pow-health` | timer | every 5 min — pipeline status then freshness |
| `pow-daily-state` | timer | hourly :25 — STATE, signals, factors, insights |
| `pow-qubic-epoch` | timer | every 10 min |
| `pow-qubic-computors` | timer | hourly :07 |
| `pow-mining-analytics` | timer | 00/06/12/18:20 |
| `pow-r2-upload` | timer | `OnUnitInactiveSec=3600` — upload only, cannot overlap itself |
| `pow-r2-retention` | timer | `OnUnitInactiveSec=1800` — verify then prune, runs even if upload fails |
| `pow-warehouse-compact` | timer | daily 00:12 |

## Hardening already applied

| Unit | Setting | Why |
|---|---|---|
| `pow-r2-upload` | `MemoryHigh=512M`, `MemoryMax=768M`, `OOMScoreAdjust=500` | OOM-killed the box before; now it is throttled early and is the preferred OOM victim, never the collectors |
| `pow-r2-retention` | `MemoryHigh=512M`, `MemoryMax=768M`, own lock file | The state file needs ~240 MB; a 64 MB cap throttled it in-kernel until it timed out |
| all `pow-*` | `ProtectSystem=strict`, `NoNewPrivileges`, `UMask=0077` | write only where `ReadWritePaths` allows |
| all services with disk writes | `POW_MIN_FREE_BYTES=2147483648` | collectors pause at 2 GiB instead of filling the disk |

## Monitoring contract

`scripts/pipeline_status.py` resolves each source's unit (timer → service) and
reports `error` when `systemctl show Result != success`. `health_check.py`
reads the resulting `warehouse/powpowpow_heartbeat.json` and fails if any
source is `stale`/`error`/`unknown`/`not_installed`.

Check them:

```bash
systemctl --user status pow-r2-upload pow-r2-retention
python3 scripts/pipeline_status.py     # 14 sources, 0 failing
python3 scripts/health_check.py        # expect {"ok": true, "failures": []}
```
