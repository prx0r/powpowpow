# ONBOARDING — start here

For a new agent working on this repo. **This file is the entry point.**
`agents.md` carries the binding rules; everything else at the root is
either a ledger or carries a `STALE` banner explaining what no longer holds.

Verified live 2026-09-25 17:34 UTC: 27/27 checks pass (re-run the script in
§6 to confirm before trusting any of it).

---

## 1. What this system is

PowPowPow continuously archives proof-of-work market and mining state, then
derives issuance-pressure metrics from it. Two sentences:

> **Backfillable truth** → fetch when needed. **Ephemeral truth** → archive
> continuously, because time destroys it.

That split is machine-readable (`core.classify_recoverability`) and documented
in `docs/data-moat-policy.md`. Everything else follows from it.

## 2. Architecture as it actually runs

```
SafeTrade WS  ─┐  collectors/l2_archival.py ──┐
QUBIC/XMR/BTC ─┼─ collectors/chain_state.py ──┼─► warehouse/raw/<chain>/<id>.json   (immutable)
REST polls     │                              └─► warehouse/normalized/<table>/chain=C/date=D/hour=H.jsonl
QUBIC epoch/computors timers ──────────────────┘
                                                          │
        pow-daily-state.timer (hourly :25) ───────────────┤ build_daily_state → signals → factors
        pow-mining-analytics.timer (6h) ──────────────────┤ btc_context / xmr / qubic analytics
        pow-warehouse-compact.timer (00:12) ──────────────┘ → warehouse/parquet/
                                                          │
        pow-r2-upload.timer (hourly :37) ─────────────────┤ scripts/r2_upload.py
                                                          │  verify size+SHA256 → delete local after HEAD
                                                          ▼
                                          Cloudflare R2  powpowpow-warehouse/powpowpow/
                                                          │
        pow-site.service  127.0.0.1:8795 ◄────────────────┘
        pow-cloudflared.service ─► https://pow.systems
```

Canonical rows carry `raw_event_id` back to one raw envelope, plus
`recoverability` (`ephemeral` | `reconstructable` | `derived`). Derived
aggregates (`daily_state`, `derived_signal`, `cross_chain_factors`) carry
**evidence instead** — contributing record IDs, `emission_source`, `poll_ids`,
coverage — because one aggregate row is built from thousands of observations.

## 3. What is running (verified, not aspirational)

Unit files are committed under `systemd/` — see `systemd/README.md` to
install them on a fresh box.

| Kind | Units | Schedule |
|---|---|---|
| services (`Restart=always`, enabled) | `pow-safetrade-l2`, `pow-chain-state`, `pow-qubic-stats`, `pow-qubic-holdings`, `pow-qubic-transfers`, `pow-site`, `pow-cloudflared` | continuous |
| timers (enabled) | `pow-health` | every 5 min |
| | `pow-qubic-epoch` | every 10 min |
| | `pow-qubic-computors` | hourly :07 |
| | `pow-daily-state` | hourly :25 |
| | `pow-r2-upload` | `OnUnitInactiveSec=3600` (1 h after each run, cannot overlap) |
| | `pow-mining-analytics` | 00/06/12/18:20 |
| | `pow-warehouse-compact` | daily 00:12 |
| | `pow-r2-retention` | `OnUnitInactiveSec=1800` (30 min after each run) |

`Linger=yes` is set, so all of it survives reboot.

**Not installed** (docs may claim otherwise): `pow-venue-l2`, `pow-venue-ws`,
`pow-signals`, `pow-factors`, `pow-analytics`, `pow-opportunity`,
`pow-miner-cards`, `pow-daily-brief`, `pow-provenance`, `pow-pearld`.

## 4. Monitoring — `/powops`

`scripts/pipeline_status.py` emits the powops contract
(`/root/powstock/POWOPS_INTEGRATION.md`):

| Route / artifact | Shape |
|---|---|
| `GET /powops` | public HTML, one row per tracked source |
| `GET /powops.json` | `{heartbeat, sources[]}`, cached 60s |
| `warehouse/powpowpow_heartbeat.json` | `heartbeat_at`, `mode`, `total_records`, `sources_run`, `sources_failed`, `results` |
| `warehouse/collector_run.json` | `source_id`, `started_at`, `status`, `error`, `duration_seconds`, `source_records_new`, `raw_new` |

`pow-health.service` runs `pipeline_status` **then** `health_check`, so a dead
timer now fails health instead of passing silently. `health_check.CHECKS`
(17 entries) covers collector heartbeats, `daily_state`, `derived_signals`,
`factors`, `computor_snapshot`, `pipeline_status`, `r2_sync`, analytics.

Status vocabulary: `ok` · `stale` · `error` · `unknown` · `not_installed`.

## 5. Commands you will actually run

```bash
cd /root/powpowpow            # NOT /home/box, NOT /home/ubuntu
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/ -q
python3 scripts/health_check.py
python3 scripts/pipeline_status.py
systemctl --user list-timers 'pow-*' --no-pager
journalctl --user -u pow-daily-state.service -n 40 --no-pager
```

Python is `/usr/bin/python3` (3.14). **There is no venv.** Dependencies are
system-installed; `requirements.txt` pins are aspirational, not installed.

Token for chat only: `~/.config/powpowpow/site.env` (mode 600). GETs are
public; only `POST /api/chat` is gated.

## 6. Verify before you trust

```bash
# 27-check live review: services, timers, artifacts, tables, R2, disk, git
# (paste the script from docs/build-progress-2026-09-25.md §verification,
#  or just run these three:)
python3 scripts/health_check.py          # expect {"ok": true, "failures": []}
curl -s https://pow.systems/powops.json  # expect "sources_failed": 0
git status --short --branch              # expect no "ahead/behind"
```

Current receipts: **121 tests pass, 0 failures**, `pipeline_status` 14 sources.
`health_check` is currently **`ok: false`** — see trap 8: the disk is full and
that is exactly the signal it is supposed to raise.

## 7. Traps

1. **Two boxes push to one branch.** Rebase before push: commit →
   `git fetch` → `git rebase origin/master` → push. Four remote commits
   landed mid-session earlier and one clobbered `warehouse/*_analytics.json`.
   Never commit a hand-regenerated artifact while another box may be writing it.
2. **`core/` package shadows `core.py`.** `core/__init__.py` re-exports from
   `core.py`. To patch module globals in tests use
   `monkeypatch.setitem(fn.__globals__, "BASE_DIR", ...)`, **not**
   `monkeypatch.setattr(core, "BASE_DIR", ...)` — that changes a different
   namespace. This caused the `isolated` fixture to write observations into the
   live warehouse — fixed in `tests/test_garden.py`, but the rule still holds.
3. **Do not rewrite stale files.** Annotate them with a `STALE` banner that
   says exactly what is wrong and points at current truth (`agents.md` §5).
   Authoritative docs live in `docs/`.
4. **Never write directional language** — no bullish/bearish/buy/sell in code
   output, UI, briefs or commits (`agents.md` §10). Signals render as
   numeric z-scores + evidence source.
5. **Never commit secrets.** Scan before push:
   `grep -rIlE "cfat_|ghp_|sk-[A-Za-z0-9]{10,}" --exclude-dir=.git .`
   Credentials come from `agent-vault vault credential get <KEY> --vault oracle`.
6. **`extracted/` is gitignored** — untracked research imports, never commit it.
7. **Regenerated data is gitignored** (`warehouse/raw`, `normalized`, `parquet`,
   heartbeats, `collector_run.json`). Tracked JSON
   (`chains/network_state.json`, `chains/factors/*`, `warehouse/*_analytics.json`)
   **is** dirty often — expect it.
8. **Disk is FULL (0 bytes free).** Both collectors now refuse to write —
   `chain_state` logs `ERR low disk`, SafeTrade logs `[DISK] waiting` (it
   re-checks every60 s while connected, not only between reconnects) — and
   `health_check` raises `check: disk`. Consumption is from **other projects**
   (`powstock/data/raw` 4.8 GB, `opencode.db` 2.5 GB), not the warehouse
   (859 MB). ~3.75 GiB must be freed to resume; ranked options in
   `docs/audit-2026-09-25.md` §B4. Below that, collectors pause
   `POW_MIN_FREE_BYTES` (2 GiB) by design. Local retention: `raw` 24 h,
   `normalized` 30 h, `parquet` 168 h, `chains/` never — and only after a
   remote `HEAD` confirms size + SHA-256.

## 8. Where things are

| I want to… | Look at |
|---|---|
| understand the storage policy | `docs/data-moat-policy.md` |
| operate the live system | `docs/pow-systems-live.md` |
| see what shipped and what's open | `docs/build-progress-2026-09-25.md` |
| see the commercial position | `docs/data-product-report-2026-09-25.md` |
| find a QUBIC endpoint | `docs/qubic-sources.md` (verified live) |
| read the binding rules | `agents.md` (banner is current) |
| write a collector | `collectors/chain_state.py` (model), `core.fetch_json` |
| change a signal | `signals.py` (every row carries evidence + assumptions) |
| change retention / R2 | `scripts/r2_upload.py`, `docs/pow-systems-live.md` |
| add a monitored source | `scripts/pipeline_status.py` `SOURCES` **and** `scripts/health_check.py` `CHECKS` |

## 9. Definition of done

1. `pytest -q` passes (or the failure is the documented one).
2. `ruff check --select E4,E7,E9,F <files you touched>` is clean — the repo
   has hundreds of pre-existing style findings in legacy files; don't
   mass-format them (a single `ruff format scripts/ tests/` once rewrote 29
   files unintentionally).
3. `health_check.py` still returns `ok: true`.
4. If you added a pipeline stage: add it to **both** `SOURCES` and `CHECKS`,
   or nobody will notice when it dies.
5. Docs updated; `git diff --check` clean; rebase then push.
