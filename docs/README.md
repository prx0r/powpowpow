# Documentation index

Start at **`../ONBOARDING.md`** if you are new to this repo. Everything else
is referenced from there.

This file exists because the repo root carries thirty-plus `.md` files, most
of them ledgers from earlier phases. Read the table below before opening
anything at the root.

## Authoritative — trust these

| File | What it answers |
|---|---|
| `../ONBOARDING.md` | What actually runs, how it is monitored, commands, traps, definition of done |
| `api.md` | Live API routes, params, auth |
| `pow-systems-live.md` | Unit/timer table, Cloudflare, R2 retention, insight metrics, verification commands |
| `qubic-sources.md` | Which QUBIC endpoints are live, dead, or collected |
| `data-moat-policy.md` | What is ephemeral vs reconstructable vs derived, and why |
| `build-progress-2026-09-25.md` | What shipped this session, receipts, open threads |
| `data-product-report-2026-09-25.md` | What compounds over 60 days, gaps, ranked next steps |

## Ledgers — current but volatile

These are maintained and still useful; they change often.

| File | Content |
|---|---|
| `../audit.md` | full inventory (individual lines drift; banner explains which) |
| `../threads.md` | ranked work threads |
| `../BLOCKERS.md` | known blockers |
| `../HANDOVER.md` | file map + key invariants |
| `../agents.md` | binding rules for agents (the rules apply; its ops section does not) |

## Stale — read the banner first

Each carries a `STALE` banner naming what is wrong and pointing at current
truth. **Do not follow them operationally and do not rewrite them** — annotate
only (`agents.md §5`).

`../README.md`, `../DOCS.md`, `../QUICKSTART.md`, `../API_DOCUMENTATION.md`,
`../TODO.md`, `../failures.md`, `../dashboard/index.html`

## Research — durable, not operational

`backfill.md` (ephemeral vs backfillable doctrine, still accurate),
`datacollection.md`, `devplancurrent.md` (thesis), `products.md`,
`01_architecture_and_vision.md` … `08_missing_data_layers_research.md`,
`unsure.md`, `devmap.md`, `transforms.md`, `canonical.md`, `content.md`,
`pr1.md`, `pr2.md`, `tier2.md`, `todo.md`.

## Out of tree

| Path | What |
|---|---|
| `../extracted/` | untracked research imports — gitignored, never commit |
| `/root/qubic-sources/` | cloned Qubic reference repos |
| `/root/powstock/POWOPS_INTEGRATION.md` | the powops contract we emit |
| `/root/.cloudflared/config.yml` | tunnel ingress |
