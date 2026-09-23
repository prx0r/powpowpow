"""
PowPowPow MCP server — the garden outlet for agents.

Tools read live warehouse tables (STATE, derived signals, factors,
live cards, briefs), never stale snapshots. Every answer carries
provenance (record IDs, versions, dates).

Transport: MCP stdio (FastMCP). Run:
    /home/ubuntu/.venvs/powpowpow/bin/python mcp_server.py
Wire into any MCP client as a stdio server with that command.
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("powpowpow")


def _rows(table):
    rows = []
    for chain in ('venue', 'safetrade'):
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', table,
                f'chain={chain}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
    return rows


def _latest(rows, key, date=None):
    best = {}
    for r in rows:
        k = r.get(key, '')
        if date and (r.get('date') or '') != date:
            continue
        stamp = r.get('generated_at') or r.get('date', '') or r.get('receive_time', '')
        if k and (k not in best or stamp > best[k][0]):
            best[k] = (stamp, r)
    return {k: v[1] for k, v in best.items()}


@mcp.tool()
def get_asset_state(symbol: str, date: str = "") -> dict:
    """Current (or date-specific) economic state per venue: mid, spread,
    depth, trade flow, coverage. The garden's core object."""
    out = [r for r in _rows('daily_state')
           if r.get('symbol', '').upper() == symbol.upper()
           and (not date or r.get('date') == date)]
    out.sort(key=lambda r: (r.get('date', ''), r.get('venue', '')))
    return {'symbol': symbol.upper(), 'states': out,
            'as_of': datetime.now(timezone.utc).isoformat()}


@mcp.tool()
def get_signals(symbol: str = "", date: str = "") -> dict:
    """Derived signals (miner_pressure, flow_pressure, required_flow) with
    drivers, evidence record IDs, assumptions, versions."""
    rows = _rows('derived_signal')
    if symbol:
        rows = [r for r in rows if r.get('asset', '').upper() == symbol.upper()]
    if date:
        rows = [r for r in rows if r.get('date') == date]
    else:
        rows = list(_latest(rows, 'asset').values()) if not symbol else rows
    return {'signals': rows}


@mcp.tool()
def get_factors(date: str = "") -> dict:
    """Cross-venue factor table: issuance, burden vs book, spreads, flow,
    joined signal directions."""
    try:
        fac = json.load(open(os.path.join(
            BASE_DIR, 'chains', 'factors', 'cross_chain_factors.json')))
    except OSError:
        fac = {}
    return {'factors': fac,
            'note': 'sell_fraction unmeasured; see sell_methodology per row'}


@mcp.tool()
def compare_compute_routes(hardware: str = "RTX_4090",
                           electricity: float = 0.10) -> dict:
    """Cheapest acceptable use of a GPU right now: mine vs rent routes
    with expected net/day. Rental asks are seeded samples until
    marketplace feeds recover."""
    from v1_live_cards import generate_card
    try:
        prices = {}
        for r in _rows('daily_state'):
            if r.get('mid_close') and r.get('symbol') not in prices:
                prices[r['symbol']] = r['mid_close']
        out = {}
        for coin in ('PRL', 'XMR', 'QUAN', 'CLORE', 'AKT', 'NOS'):
            try:
                card = generate_card(coin, prices.get(coin, 0),
                                     electricity=electricity)
                hw = (card.get('hardware') or {}).get(hardware)
                if hw:
                    out[coin] = hw
            except Exception as e:
                out[coin] = {'error': str(e)[:100]}
        return {'hardware': hardware, 'routes': out,
                'methodology': 'rig/network * emission * price; rental = ask*24 @100% util'}
    except Exception as e:
        return {'error': str(e)[:200]}


@mcp.tool()
def get_miner_pressure(symbol: str) -> dict:
    """Miner-pressure evidence bundle for one asset: latest signals,
    factor row, chain telemetry pointers."""
    sym = symbol.upper()
    signals = [r for r in _rows('derived_signal') if r.get('asset') == sym]
    signals.sort(key=lambda r: r.get('generated_at', ''), reverse=True)
    try:
        fac = json.load(open(os.path.join(
            BASE_DIR, 'chains', 'factors', 'cross_chain_factors.json'))).get(sym)
    except OSError:
        fac = None
    try:
        net = json.load(open(os.path.join(
            BASE_DIR, 'chains', 'network_state.json'))).get(sym)
    except OSError:
        net = None
    return {'asset': sym, 'signals': signals[:6], 'factor': fac,
            'network': net}


@mcp.tool()
def get_brief(date: str = "") -> dict:
    """Latest (or dated) PowDaily brief: signal board, movers, flow watch."""
    if not date:
        files = sorted(glob.glob(os.path.join(BASE_DIR, 'briefs', '*.md')))
        if not files:
            return {'error': 'no briefs yet'}
        date = os.path.splitext(os.path.basename(files[-1]))[0]
    try:
        return {'date': date,
                'brief': open(os.path.join(BASE_DIR, 'briefs', f'{date}.md')).read()}
    except OSError:
        return {'error': f'no brief for {date}'}


@mcp.tool()
def get_price_history(symbol: str, days: int = 90) -> dict:
    """Daily closes + volumes (CoinGecko 365d + venue mids). The outcome
    variable for backtests and Seesaw lag analysis."""
    sym = symbol.upper()
    rows = [r for r in _rows('price_history')
            if (r.get('symbol') or '').upper() == sym]
    rows.sort(key=lambda r: r.get('date', ''))
    if days and len(rows) > days:
        rows = rows[-days:]
    mids = [{'date': r.get('date'), 'mid_close': r.get('mid_close'),
             'venue': r.get('venue')}
            for r in _rows('daily_state')
            if (r.get('symbol') or '').upper() == sym and r.get('mid_close')]
    mids.sort(key=lambda r: r['date'] or '')
    return {'symbol': sym, 'closes': rows, 'venue_mids': mids[-days:] if days else mids}


@mcp.tool()
def get_health() -> dict:
    """Garden health: what's collecting, row counts, history depth,
    service status. Start here when asking what we actually have."""
    import glob as _glob
    tables = {}
    for t in sorted(os.listdir(os.path.join(BASE_DIR, 'warehouse', 'normalized'))):
        n = 0
        dates = set()
        for f in _glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', t,
                'chain=*', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    n += 1
                    try:
                        r = json.loads(line)
                        d = (r.get('exchange_time') if isinstance(
                            r.get('exchange_time'), str) else None) or r.get('date') or ''
                        if isinstance(d, str) and len(d) >= 10:
                            dates.add(d[:10])
                    except ValueError:
                        pass
        tables[t] = {'rows': n, 'dates': len(dates),
                     'from': min(dates) if dates else None,
                     'to': max(dates) if dates else None}
    return {'tables': tables,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'notes': 'seed JSONL dropped after Parquet compact; '
                     'parquet/ holds Jul-Aug-Sep firsts; venue daemons live'}


@mcp.tool()
def get_live() -> dict:
    """Live venue mids from latest daily STATE + collector heartbeats.
    Same source the dashboard ticker polls every 5s."""
    live = {}
    for sym_full in ('xmrusdt', 'qubicusdt', 'prlusdt', 'nockusdt',
                     'kasusdt', 'xelusdt', 'xtmusdt', 'xmrbtc'):
        rows = [r for r in _rows('daily_state')
                if (r.get('symbol') or '').lower() == sym_full]
        rows.sort(key=lambda r: r.get('observed_at', ''), reverse=True)
        if rows:
            r = rows[0]
            live[sym_full] = {
                'symbol': sym_full.replace('usdt', '').replace('btc', '').upper(),
                'mid': r.get('mid_close'),
                'spread_bps': r.get('spread_bps_median'),
                'bid_depth': r.get('bid_notional_20_mean'),
                'venue': r.get('venue'),
                'updated': r.get('observed_at'),
            }
    return {'live': live,
            'as_of': datetime.now(timezone.utc).isoformat()}


@mcp.tool()
def get_xmr_full() -> dict:
    """Full XMR bundle: emission, 365d position, miner benchmarks,
    p2pool, network telemetry, 90d closes. The golden-child view."""
    try:
        ax = json.load(open(os.path.join(
            BASE_DIR, 'warehouse', 'xmr_analytics.json')))
    except (OSError, ValueError):
        ax = {}
    try:
        net = json.load(open(os.path.join(
            BASE_DIR, 'chains', 'network_state.json'))).get('XMR', {})
    except OSError:
        net = {}
    closes = [{'date': r.get('date'), 'close': r.get('close_usd')}
              for r in _rows('price_history')
              if (r.get('symbol') or '').upper() == 'XMR' and r.get('close_usd')]
    closes.sort(key=lambda x: x['date'])
    return {'emission': ax.get('emission', {}),
            'price_position': ax.get('price_position_365d', {}),
            'miner_benchmarks': ax.get('miner_cost_benchmark', []),
            'p2pool': ax.get('network', {}).get('p2pool', {}),
            'network': net, 'closes': closes[-90:]}


@mcp.tool()
def get_opportunity(hardware: str = "", date: str = "") -> dict:
    """Daily ranked opportunity set per hardware archetype: every route
    (mine/rent/idle) with expected net, best_action, model version and
    prediction hash. The counterfactual record — what an agent would
    have done. Start here for 'what should this machine do'."""
    rows = _rows('opportunity_snapshot')
    if hardware:
        rows = [r for r in rows if (r.get('hardware') or '').upper() == hardware.upper()]
    if date:
        rows = [r for r in rows if r.get('date') == date]
    else:
        rows = list(_latest(rows, 'hardware').values()) if not hardware else rows
    rows.sort(key=lambda r: (r.get('date', ''), r.get('hardware', '')))
    return {'snapshots': rows[-30:]}


@mcp.tool()
def recommend_homelab(electricity: float = 0.10) -> dict:
    """Detect THIS machine's hardware and join to the opportunity set:
    inventory with provenance, matched archetypes, ranked routes,
    best_action and prediction hashes. Read-only; no execution.
    The XMRBot-flow entry point: detect -> query -> (policy/grant/execute
    live outside the garden)."""
    try:
        import homelab as _hl
    except Exception as e:
        return {'error': f'homelab adapter unavailable: {str(e)[:100]}'}
    try:
        inv = _hl.inventory(electricity=electricity)
        return _hl.recommend(inv, electricity=electricity)
    except Exception as e:
        return {'error': str(e)[:200]}


if __name__ == '__main__':
    mcp.run()
