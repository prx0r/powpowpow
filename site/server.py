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

TOKEN = os.environ.get('POW_SITE_TOKEN', secrets.token_urlsafe(24))
PORT = int(os.environ.get('POW_SITE_PORT', '8795'))
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

SYS_PROMPT = """You are the PowPowPow analyst, explaining where AI, compute,
energy, crypto and physical bottlenecks intersect. You answer from the
garden data pasted with each question (STATE, signals with drivers and
evidence, factors). Rules: explain mechanics and evidence, never give
financial recommendations or buy/sell calls. If data is missing, say
exactly what is unmeasured. Be concise and concrete with numbers."""


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
    for sym in ('xmr', 'qubic', 'prl', 'kas', 'nock'):
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
    """Compact evidence pack for the chat model."""
    sym = symbol.upper()
    states = [r for r in _rows('daily_state')
              if (not sym or (r.get('symbol') or '').upper() == sym)]
    states.sort(key=lambda r: (r.get('date', ''), r.get('venue', '')))
    sigs = [r for r in _rows('derived_signal')
            if (not sym or (r.get('asset') or '').upper() == sym)]
    try:
        fac = json.load(open(os.path.join(
            ROOT, 'chains', 'factors', 'cross_chain_factors.json')))
        if sym:
            fac = {sym: fac.get(sym)}
    except OSError:
        fac = {}
    return {'states': states[-12:], 'signals': sigs[-12:], 'factors': fac}


def _chat(message):
    ctx = _garden_context()
    prompt = (f"Garden evidence (latest STATE, signals, factors):\n"
              f"{json.dumps(ctx, default=str)[:6000]}\n\nQuestion: {message}")
    try:
        from agentcom.pi_agent import chat as pi_chat
        r = pi_chat(prompt, system_prompt=SYS_PROMPT)
        reply = r.get('reply', '(no response)')
        return {'reply': reply, 'via': 'pi-harness/opencode-go',
                'tools_called': r.get('tools_called', [])}
    except Exception as e:
        # Data-only fallback: answer from tables, no LLM.
        return {'reply': _data_answer(message, ctx),
                'via': f'data-fallback (harness down: {str(e)[:100]})',
                'tools_called': []}


def _data_answer(message, ctx):
    m = message.lower()
    for s in ctx['signals']:
        if s.get('asset', '').lower() in m:
            return (f"{s['asset']} {s['signal']} ({s.get('version')}): "
                    f"{s.get('direction')} {s.get('strength')}. Drivers: "
                    f"{'; '.join(s.get('drivers', []))}. Assumptions: "
                    f"{'; '.join(s.get('assumptions', [])[:2])}")
    top = sorted(ctx['signals'], key=lambda s: s.get('strength', 0) or 0,
                 reverse=True)[:5]
    if top and any(w in m for w in ('signal', 'top', 'screener', 'today')):
        return 'Strongest signals: ' + '; '.join(
            f"{s['asset']} {s['signal']} {s['direction']} {s['strength']}"
            for s in top)
    return ('I answer from garden tables (STATE, signals, factors). '
            'Ask about an asset (e.g. XMR, QUBIC) or "top signals". '
            'The LLM harness is unreachable right now.')


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
