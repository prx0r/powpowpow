"""
PowPowPow consumer site — forked from the qpbot dashboard setup.

Same ops pattern: stdlib only, token gate (?token=), loopback bind,
systemd supervised. Outside world arrives via Cloudflare tunnel
(hostname -> 127.0.0.1:PORT, see ~/.cloudflared/*.yml pattern).

Content is pure garden: STATE, derived signals, factors, live cards,
briefs, compiled pages. Chat routes through the Pi harness
(agentcom.pi_agent, opencode-go backend) with garden context injected;
analytical-framing rule enforced in the system prompt (explain, never
recommend). Falls back to data-only answers if the harness is down.
"""

from __future__ import annotations

import glob
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, '/home/ubuntu/qpbot')  # pi harness (same as qpbot dash)

# Fix core/ package shadowing core.py
try:
    from core import utcnow as _utcnow  # noqa: F401
except (ImportError, AttributeError):
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location('_core_py', os.path.join(ROOT, 'core.py'))
    _core = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_core)
    import sys as _sys
    _sys.modules['core'] = _core

TOKEN = os.environ.get('POW_SITE_TOKEN', secrets.token_urlsafe(24))
PORT = int(os.environ.get('POW_SITE_PORT', '8795'))
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

SYS_PROMPT = """You are the PowPowPow analyst — a data terminal for mining economics.
You explain where AI, compute, energy, crypto and physical bottlenecks intersect.

RULES:
1. Answer from the garden evidence pasted with each question.
2. Never give financial recommendations or buy/sell calls.
3. If data is missing, say exactly what is unmeasured.
4. Be concise. Numbers, not essays.
5. When asked about a coin, lead with the money math: emission, burn, burden, spread, flow.
6. Explain jargon: "burden" = one day of fresh supply value vs resting bids.
   "spread" = gap between best buy and sell in basis points.
   "flow" = aggressive buy minus sell in a window.
7. For Qubic: emphasize epoch = 7-day week, burn share = 78.75% since Aug 2026,
   gross = 1T/week constant, net = what reaches market. Computors earn rewards.
8. For XMR: 0.6 XMR per 2-min block forever = 432/day, no halvings.
   Pool flows hidden by design — we measure drip vs demand, not wallet labels."""


def _rows(table):
    rows = []
    for chain in ('venue', 'safetrade'):
        for f in glob.glob(os.path.join(
                ROOT, 'warehouse', 'normalized', table,
                f'chain={chain}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
    for sym in ('xmr', 'qubic', 'prl', 'kas', 'nock', 'btc', 'akt'):
        for f in glob.glob(os.path.join(
                ROOT, 'warehouse', 'normalized', table,
                f'chain={sym}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
    return rows


def _garden_context(symbol=''):
    """Focused evidence pack for the chat model (QUBIC/XMR deep, others lean)."""
    sym = symbol.upper()
    # Always include the latest signal + factor row for context
    sigs = [r for r in _rows('derived_signal')
            if (not sym or (r.get('asset') or '').upper() == sym)]
    sigs.sort(key=lambda r: r.get('generated_at', ''), reverse=True)
    sig = sigs[0] if sigs else {}
    try:
        fac = json.load(open(os.path.join(
            ROOT, 'chains', 'factors', 'cross_chain_factors.json')))
        fac = fac.get(sym, {})
    except OSError:
        fac = {}
    try:
        net = json.load(open(os.path.join(
            ROOT, 'chains', 'network_state.json'))).get(sym, {})
    except OSError:
        net = {}
    return {
        'symbol': sym,
        'signal': sig,
        'factor': fac,
        'network': net,
    }


def _chat(message):
    # Auto-detect which coin the question is about for focused context
    msg_lower = message.lower()
    sym = ''
    for s in ['qubic', 'xmr', 'monero', 'prl', 'pearl', 'kas', 'kaspa',
              'nock', 'nockchain', 'xel', 'xelis']:
        if s in msg_lower:
            sym = s.upper().replace('MONERO', 'XMR').replace('PEARL', 'PRL').replace('KASPA', 'KAS').replace('NOCKCHAIN', 'NOCK').replace('XELIS', 'XEL')
            break
    ctx = _garden_context(sym)
    prompt = (f"Garden evidence:\n"
              f"{json.dumps(ctx, default=str)[:4000]}\n\n"
              f"Question: {message}")
    try:
        from agentcom.pi_agent import chat as pi_chat
        r = pi_chat(prompt, system_prompt=SYS_PROMPT)
        reply = r.get('reply', '(no response)')
        return {'reply': reply, 'via': 'pi-harness/opencode-go',
                'tools_called': r.get('tools_called', [])}
    except Exception as e:
        return {'reply': _data_answer(message, ctx),
                'via': f'data-fallback (harness down: {str(e)[:100]})',
                'tools_called': []}


def _data_answer(message, ctx):
    m = message.lower()
    sym = ctx.get('symbol', '')
    net = ctx.get('network', {})
    sig = ctx.get('signal', {})
    if sym == 'QUBIC' and net:
        em = net.get('daily_emission')
        net_str = f"{em/1e9:.1f}B/d" if em else 'unknown'
        return (f"QUBIC: epoch {net.get('epoch')} ({net.get('epoch_progress',0)*100:.1f}%), "
                f"burn {net.get('burn_rate',0)*100:.2f}%, "
                f"net {net_str}. "
                f"{net.get('computors',0)} computors, {net.get('doge_tasks','?')} doge tasks. "
                f"{net.get('total_transactions',0):,} transactions.")
    if sig:
        return f"{sym}: {sig.get('signal')} {sig.get('direction')} {sig.get('strength')}. Drivers: {', '.join(sig.get('drivers', []))}."
    return (f'No deep data for "{sym}" yet. Try QUBIC or XMR.' if sym else
            'Ask about a specific coin: QUBIC, XMR, PRL, KAS, NOCK, XEL.')


def _analysis(symbol):
    """Per-asset derived analysis (Seesaw loops, epoch returns).

    XMR: price vs difficulty (30d changes + correlation over joint
    history). QUBIC: trailing 7d epoch-equivalent returns from CG
    closes (exact epoch boundaries pending tick-map history).
    """
    out = {'symbol': symbol, 'analysis': {}}
    if symbol == 'XMR':
        prices = sorted(
            ((r.get('date'), r.get('close_usd')) for r in _rows('price_history')
             if (r.get('symbol') or '').upper() == 'XMR' and r.get('close_usd')),
            key=lambda x: x[0] or '')
        diffs = sorted(
            ((r.get('observed_at', '')[:10], r.get('difficulty')) for r in _rows('chain_snapshot')
             if (r.get('network_id') or '') == 'xmr'
             and r.get('difficulty') and float(r['difficulty']) > 1e6),
            key=lambda x: x[0])
        a = out['analysis']
        if len(prices) >= 31:
            a['price_30d_pct'] = round((prices[-1][1] - prices[-31][1]) / prices[-31][1], 4)
        if len(diffs) >= 2:
            a['difficulty_latest'] = diffs[-1][1]
            first, last = diffs[0][1], diffs[-1][1]
            a['difficulty_change'] = round((last - first) / first, 4) if first else None
            a['difficulty_window'] = f"{diffs[0][0]} → {diffs[-1][0]}"
            a['difficulty_points'] = len(diffs)
        # joint correlation where dates overlap
        pmap = dict(prices)
        pairs = [(pmap[d], df) for d, df in diffs if d in pmap and pmap[d]]
        a['difficulty_range'] = f"{diffs[0][0]} → {diffs[-1][0]}"
        if len(pairs) >= 5:
            import math
            xs = [math.log(p) for p, _ in pairs]
            ys = [math.log(d) for _, d in pairs]
            # Filter out same-day pairs (correlation needs spread across days)
            unique_dates = sorted(set(d for d, _ in diffs))
            if len(unique_dates) >= 2:
                mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
                num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
                a['logprice_logdiff_corr'] = round(num / den, 3) if den else None
                a['corr_n'] = len(pairs)
            else:
                a['corr_note'] = 'all difficulty readings on same day — need multi-day history'
        a['method'] = ('price 365d (CoinGecko) vs difficulty (localmonero '
                       'polls, accumulates daily)')
    elif symbol == 'QUBIC':
        closes = sorted(
            ((r.get('date'), r.get('close_usd')) for r in _rows('price_history')
             if (r.get('symbol') or '').upper() == 'QUBIC' and r.get('close_usd')),
            key=lambda x: x[0] or '')
        weeks = []
        for i in range(7, min(len(closes), 7 * 12), 7):
            a, b = closes[-i - 7][1], closes[-i][1]
            weeks.append(round((b - a) / a, 4) if a else None)
        out['analysis'] = {
            'epoch_equiv_weekly_returns': list(reversed(weeks)),
            'method': ('trailing 7d windows (exact epoch boundaries pending '
                       'tick-map history); latest first')}
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = 'PowSite/1.0'

    def _gate(self):
        q = parse_qs(urlparse(self.path).query)
        return q.get('token', [''])[0] == TOKEN

    def _send(self, body, ctype='application/json', code=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, default=str).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._gate():
            return self._send({'error': 'bad token'}, code=403)
        u = urlparse(self.path)
        q = parse_qs(u.query)
        arg = lambda k, d='': q.get(k, [d])[0]

        if u.path in ('/', '/index.html'):
            return self._send(open(os.path.join(STATIC, 'index.html'), 'rb').read(),
                              'text/html')
        if u.path == '/api/health':
            return self._send({'ok': True,
                               'time': datetime.now(timezone.utc).isoformat()})
        if u.path == '/api/factors':
            try:
                fac = json.load(open(os.path.join(
                    ROOT, 'chains', 'factors', 'cross_chain_factors.json')))
            except OSError:
                fac = {}
            return self._send({'factors': fac})
        if u.path == '/api/signals':
            rows = _rows('derived_signal')
            sym, date = arg('symbol').upper(), arg('date')
            if sym:
                rows = [r for r in rows if (r.get('asset') or '').upper() == sym]
            if date:
                rows = [r for r in rows if r.get('date') == date]
            rows.sort(key=lambda r: r.get('generated_at', ''), reverse=True)
            return self._send({'signals': rows[:200]})
        if u.path == '/api/state':
            rows = _rows('daily_state')
            sym, date = arg('symbol').upper(), arg('date')
            if sym:
                rows = [r for r in rows if (r.get('symbol') or '').upper() == sym]
            if date:
                rows = [r for r in rows if r.get('date') == date]
            rows.sort(key=lambda r: (r.get('date', ''), r.get('venue', '')))
            return self._send({'states': rows[-60:]})
        if u.path == '/api/cards':
            try:
                from v1_live_cards import generate_card
                prices = {}
                for r in _rows('daily_state'):
                    if r.get('mid_close') and r.get('symbol') not in prices:
                        prices[r['symbol']] = r['mid_close']
                out = {}
                for coin in ('PRL', 'QUBIC', 'XMR', 'KAS', 'QUAN', 'CLORE',
                             'AKT', 'NOS'):
                    try:
                        out[coin] = generate_card(coin, prices.get(coin, 0))
                    except Exception as e:
                        out[coin] = {'error': str(e)[:100]}
                return self._send({'cards': out})
            except Exception as e:
                return self._send({'error': str(e)[:200]}, code=500)
        if u.path == '/api/brief':
            date = arg('date')
            files = sorted(glob.glob(os.path.join(ROOT, 'briefs', '*.md')))
            if not files:
                return self._send({'error': 'no briefs'})
            if not date:
                date = os.path.splitext(os.path.basename(files[-1]))[0]
            try:
                return self._send({'date': date, 'brief': open(
                    os.path.join(ROOT, 'briefs', f'{date}.md')).read()})
            except OSError:
                return self._send({'error': f'no brief {date}'}, code=404)
        if u.path == '/api/page':
            sym = arg('symbol').upper()
            try:
                return self._send({'symbol': sym, 'page': open(
                    os.path.join(ROOT, 'pages', f'{sym}.md')).read()})
            except OSError:
                return self._send({'error': f'no page {sym}'}, code=404)
        if u.path == '/api/analysis':
            return self._send(_analysis(arg('symbol').upper()))
        if u.path == '/api/history':
            sym = arg('symbol').upper()
            out = [r for r in _rows('price_history')
                   if (r.get('symbol') or '').upper() == sym]
            out.sort(key=lambda r: r.get('date', ''))
            return self._send({'symbol': sym, 'closes': [
                {'date': r.get('date'), 'close': r.get('close_usd'),
                 'volume': r.get('volume_usd')} for r in out]})
        if u.path == '/api/cards_history':
            sym = arg('symbol').upper()
            out = [r for r in _rows('miner_card')
                   if (r.get('coin') or '').upper() == sym]
            out.sort(key=lambda r: (r.get('date', ''), r.get('hardware', '')))
            return self._send({'symbol': sym, 'cards': out[-200:]})
        if u.path == '/api/state_series':
            sym = arg('symbol').upper()
            rows = [r for r in _rows('daily_state')
                    if (r.get('symbol') or '').upper() == sym]
            rows.sort(key=lambda r: (r.get('date', ''), r.get('venue', '')))
            # Aggregate cross-venue per date: burden, spread, flow
            by_date = {}
            for r in rows:
                d = r.get('date', '')
                a = by_date.setdefault(d, {'burden': 0, 'bid': 0, 'spread': [],
                                            'buy': 0, 'sell': 0, 'trades': 0,
                                            'n': 0, 'venues': []})
                a['bid'] += r.get('bid_notional_20_mean') or 0
                if r.get('spread_bps_median') is not None:
                    a['spread'].append(r['spread_bps_median'])
                a['buy'] += r.get('trade_buy_notional') or 0
                a['sell'] += r.get('trade_sell_notional') or 0
                a['trades'] += r.get('n_trades') or 0
                a['n'] += 1
                a['venues'].append(r.get('venue'))
            series = []
            for d in sorted(by_date):
                a = by_date[d]
                import statistics as _st
                spread = _st.median(a['spread']) if a['spread'] else None
                imb = (a['buy'] - a['sell']) / (a['buy'] + a['sell']) if (a['buy'] + a['sell']) > 0 else None
                series.append({'date': d, 'spread': spread, 'buy': a['buy'],
                               'sell': a['sell'], 'imbalance': imb, 'trades': a['trades'],
                               'venues': a['venues']})
            return self._send({'symbol': sym, 'series': series})
        if u.path == '/api/epoch_series':
            rows = _rows('qubic_epoch')
            rows.sort(key=lambda r: (r.get('epoch', 0), r.get('observed_at', '')))
            return self._send({'rows': rows[-30:]})
        if u.path == '/api/analytics':
            sym = arg('symbol').upper()
            f = os.path.join(ROOT, 'warehouse', f'{sym.lower()}_analytics.json')
            try:
                return self._send(json.load(open(f)))
            except (OSError, ValueError):
                return self._send({'error': f'no analytics for {sym} (run scripts/{sym.lower()}_analytics.py)'}, code=404)
        if u.path == '/api/ops':
            import subprocess as _sp
            ops = {'heartbeats': {}, 'services': {}}
            for name in ('venue_l2_heartbeat.json', 'venue_ws_heartbeat.json',
                         'chain_state_heartbeat.json', 'safetrade_l2_heartbeat.json'):
                try:
                    ops['heartbeats'][name] = json.load(open(os.path.join(
                        ROOT, 'warehouse', name)))
                except OSError:
                    pass
            for svc in ('pow-venue-l2', 'pow-venue-ws', 'pow-chain-state',
                        'pow-safetrade-l2', 'pow-pearld', 'pow-site'):
                try:
                    r = _sp.run(['systemctl', '--user', 'is-active', svc + '.service'],
                                capture_output=True, text=True, timeout=5)
                    ops['services'][svc] = r.stdout.strip()
                except Exception:
                    ops['services'][svc] = 'unknown'
            return self._send(ops)
        if u.path == '/api/chain':
            sym = arg('symbol').upper()
            try:
                net = json.load(open(os.path.join(
                    ROOT, 'chains', 'network_state.json'))).get(sym)
            except OSError:
                net = None
            fund = {}
            try:
                fund = json.load(open(os.path.join(
                    ROOT, 'chains', 'chain_fundamentals.json'))).get(sym, {})
            except OSError:
                pass
            snaps = [r for r in _rows('chain_snapshot')]
            return self._send({'symbol': sym, 'network': net,
                               'fundamentals': fund,
                               'snapshots': len(snaps)})
        if u.path == '/api/ticks':
            # Live tick stream (SSE): freshest orderbook mid per symbol,
            # sourced from continuous normalized rows (NOT daily STATE).
            # EventSource auto-reconnects; each connection capped at 5min.
            import time as _t
            syms = [s.strip().lower() for s in
                    (arg('symbols') or 'btcusdt,xmrusdt,qubicusdt').split(',') if s.strip()]

            def _tail(path, n=400):
                try:
                    with open(path, 'rb') as f:
                        f.seek(0, 2)
                        size = f.tell()
                        block, lines = 8192, []
                        while len(lines) <= n and size > 0:
                            step = min(block, size)
                            size -= step
                            f.seek(size)
                            lines = f.read().splitlines() + lines
                            block *= 2
                    return [ln.decode('utf-8', 'replace') for ln in lines[-n:]]
                except OSError:
                    return []

            def _latest_ticks():
                import datetime as _dt
                today = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d')
                best = {}
                for chain in ('safetrade', 'venue'):
                    for f in glob.glob(os.path.join(
                            ROOT, 'warehouse', 'normalized', 'orderbook_snapshot',
                            f'chain={chain}', f'date={today}', 'hour=*.jsonl')):
                        for ln in _tail(f):
                            try:
                                r = json.loads(ln)
                            except ValueError:
                                continue
                            s = (r.get('symbol') or '').lower()
                            if s in syms and r.get('mid') and (
                                    s not in best or (r.get('receive_time', '') > best[s].get('receive_time', ''))):
                                best[s] = r
                out = {}
                for s in syms:
                    r = best.get(s)
                    if not r:
                        continue
                    try:
                        age = (_dt.datetime.now(_dt.timezone.utc) - _dt.datetime.fromisoformat(
                            r['receive_time'].replace('Z', '+00:00'))).total_seconds()
                    except Exception:
                        age = None
                    base = s
                    for q in ('usdt', 'usdc', 'btc', 'xmr', 'safe'):
                        if base.endswith(q) and len(base) > len(q):
                            base = base[:-len(q)]
                            break
                    out[s] = {'symbol': base.upper(),
                              'mid': r.get('mid'), 'spread_bps': r.get('spread_bps'),
                              'venue': r.get('venue'), 'age_s': round(age) if age is not None else None,
                              'updated': r.get('receive_time')}
                return out

            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            t0 = _t.time()
            try:
                while _t.time() - t0 < 300:
                    body = json.dumps({'live': _latest_ticks(),
                                       't': datetime.now(timezone.utc).isoformat()},
                                      default=str)
                    self.wfile.write(f"data: {body}\n\n".encode())
                    self.wfile.flush()
                    _t.sleep(2)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        if u.path == '/api/live':
            live = {}
            for sym_full in ('xmrusdt', 'qubicusdt', 'prlusdt', 'nockusdt',
                             'kasusdt', 'xelusdt', 'xtmusdt', 'xmrbtc',
                             'btcusdt'):
                rows = [r for r in _rows('daily_state')
                        if (r.get('symbol') or '').lower() == sym_full]
                if not rows:
                    rows = [r for r in _rows('daily_state')
                            if (r.get('symbol') or '').lower().startswith(sym_full.replace('usdt', '').replace('btc', ''))]
                rows.sort(key=lambda r: r.get('observed_at', ''), reverse=True)
                if rows:
                    r = rows[0]
                    live[sym_full] = {
                        'symbol': sym_full.replace('usdt', '').replace('btc', '').upper(),
                        'mid': r.get('mid_close'),
                        'spread_bps': r.get('spread_bps_median'),
                        'bid_depth': r.get('bid_notional_20_mean'),
                        'buy_notional': r.get('trade_buy_notional'),
                        'sell_notional': r.get('trade_sell_notional'),
                        'n_trades': r.get('n_trades'),
                        'venue': r.get('venue'),
                        'updated': r.get('observed_at'),
                    }
            hb = {}
            for name in ('safetrade_l2_heartbeat.json', 'venue_l2_heartbeat.json'):
                try:
                    hb[name] = json.load(open(os.path.join(
                        ROOT, 'warehouse', name)))
                except OSError:
                    pass
            return self._send({'live': live, 'heartbeats': hb})
        if u.path == '/api/btc':
            try:
                ctx = json.load(open(os.path.join(ROOT, 'warehouse', 'btc_context.json')))
            except (OSError, ValueError):
                ctx = {'error': 'no btc context (run scripts/btc_context.py)'}
            return self._send(ctx)
        if u.path == '/api/btc_series':
            by_date = {}
            for r in _rows('chain_snapshot'):
                has_btc_field = any(r.get(k) is not None for k in (
                    'network_hashrate_ths', 'difficulty', 'miners_revenue_usd',
                    'fees_usd_day', 'price_usd', 'height',
                    'tx_count_day', 'tx_volume_usd_day',
                    'circulating_supply', 'avg_block_size_mb',
                    'unique_addresses_day', 'cost_per_tx_usd'))
                if not has_btc_field:
                    continue
                d = (r.get('event_time') or '')[:10] or (r.get('observed_at') or '')[:10]
                if not d:
                    continue
                a = by_date.setdefault(d, {})
                for k in ('network_hashrate_ths', 'difficulty',
                          'miners_revenue_usd', 'fees_usd_day',
                          'price_usd', 'height', 'next_retarget',
                          'tx_count_day', 'tx_volume_usd_day',
                          'circulating_supply', 'avg_block_size_mb',
                          'unique_addresses_day', 'cost_per_tx_usd'):
                    if r.get(k) is not None and (k not in a or r.get('source_role') == 'history-backfill'):
                        a[k] = r[k]
            series = [{'date': d, **v} for d, v in sorted(by_date.items())]
            return self._send({'series': series})
        if u.path == '/api/opportunity':
            hw, date = arg('hardware').upper(), arg('date')
            rows = _rows('opportunity_snapshot')
            if hw:
                rows = [r for r in rows if (r.get('hardware') or '').upper() == hw]
            if date:
                rows = [r for r in rows if r.get('date') == date]
            rows.sort(key=lambda r: (r.get('date', ''), r.get('hardware', '')))
            return self._send({'snapshots': rows[-30:]})
        if u.path == '/api/xmr_full':
            try:
                ax = json.load(open(os.path.join(
                    ROOT, 'warehouse', 'xmr_analytics.json')))
            except (OSError, ValueError):
                ax = {}
            net_state = {}
            try:
                net_state = json.load(open(os.path.join(
                    ROOT, 'chains', 'network_state.json'))).get('XMR', {})
            except OSError:
                pass
            closes = []
            for r in _rows('price_history'):
                if (r.get('symbol') or '').upper() == 'XMR' and r.get('close_usd'):
                    closes.append({'date': r['date'], 'close': r['close_usd'],
                                   'volume': r.get('volume_usd')})
            closes.sort(key=lambda x: x['date'])
            return self._send({
                'analytics': ax,
                'network': net_state,
                'closes': closes[-90:],
                'miner_benchmarks': ax.get('miner_cost_benchmark', []),
                'emission': ax.get('emission', {}),
                'price_position': ax.get('price_position_365d', {}),
                'p2pool': ax.get('network', {}).get('p2pool', {}),
            })
        return self._send({'error': 'not found'}, code=404)

    def do_POST(self):
        if not self._gate():
            return self._send({'error': 'bad token'}, code=403)
        u = urlparse(self.path)
        if u.path == '/api/chat':
            try:
                body = json.loads(self.rfile.read(
                    int(self.headers.get('Content-Length', 0)) or 0) or b'{}')
            except ValueError:
                body = {}
            return self._send(_chat(body.get('message', '')))
        return self._send({'error': 'not found'}, code=404)

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print(f"powpowpow site token: {TOKEN}", flush=True)
    print(f"http://localhost:{PORT}/?token={TOKEN}", flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
