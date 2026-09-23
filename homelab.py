"""
Homelab adapter — detect local hardware, join to POW opportunity set.

XMRBot flow, read-only half (no executor, no grants):
    detect  -> inventory with per-field provenance (source + UTC time)
    query   -> latest opportunity_snapshot per matched hardware archetype
    report  -> ranked routes, best_action, expected net, assumptions

Stdlib only, zero dependencies, graceful degradation: every detector
returns what it could measure with its source, never fabricates.
Missing tools (nvidia-smi, lspci) or missing registry benchmarks are
disclosed, not defaulted.

Fingerprint: sha256 over stable identity fields (model names, counts,
memory), truncated. No serials ever collected.

Future: Device-SMI (Apache-2.0) could replace the /proc + smi parsing
with one call; kept stdlib-first to match the site's stdlib-only rule
and to avoid a new dependency before the loop has scars.
"""

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

ELECTRICITY_DEFAULT = 0.10  # USD/kWh input, not a constant (see unsure.md Q4)


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _run(cmd, timeout=10):
    """Run a command, return stdout or None. Never raises."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
        return None
    except Exception:
        return None


def detect_cpu():
    """CPU model, topology, feature flags from /proc/cpuinfo (+lscpu)."""
    out = {'model': None, 'threads': None, 'sockets': None,
           'cores_per_socket': None, 'flags': [], 'randomx_notes': None,
           'sources': [], 'observed_at': utcnow()}
    try:
        with open('/proc/cpuinfo') as f:
            text = f.read()
        models = re.findall(r'^model name\s*:\s*(.+)$', text, re.M)
        if models:
            out['model'] = models[0].strip()
        out['threads'] = len(re.findall(r'^processor\s*:', text, re.M)) or None
        m = re.search(r'^flags\s*:\s*(.+)$', text, re.M)
        if m:
            out['flags'] = m.group(1).split()
        out['sources'].append('/proc/cpuinfo')
    except OSError:
        pass
    lscpu = _run(['lscpu'])
    if lscpu:
        out['sources'].append('lscpu')
        for key, dest in (('Socket(s):', 'sockets'), ('Core(s) per socket:', 'cores_per_socket')):
            m = re.search(rf'^{re.escape(key)}\s*(\d+)', lscpu, re.M)
            if m:
                out[dest] = int(m.group(1))
    flags = set(out['flags'])
    notes = []
    if 'aes' in flags:
        notes.append('AES-NI present (RandomX friendly)')
    else:
        notes.append('no AES-NI flag — RandomX will be slow')
    if 'avx2' in flags:
        notes.append('AVX2 present')
    out['randomx_notes'] = '; '.join(notes) if out['model'] else None
    return out


def detect_memory():
    """System RAM from /proc/meminfo. No DIMM detail without sudo dmidecode."""
    out = {'total_gb': None, 'sources': [], 'observed_at': utcnow()}
    try:
        with open('/proc/meminfo') as f:
            m = re.search(r'^MemTotal:\s*(\d+)\s*kB', f.read(), re.M)
        if m:
            out['total_gb'] = round(int(m.group(1)) / 1024 / 1024, 1)
            out['sources'].append('/proc/meminfo')
    except OSError:
        pass
    return out


def detect_gpus():
    """GPUs via nvidia-smi, then lspci fallback. Each entry carries source."""
    gpus = []
    nv = _run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version,power.limit',
               '--format=csv,noheader,nounits'])
    if nv:
        for line in nv.strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2 and parts[0]:
                gpus.append({
                    'name': parts[0],
                    'memory_mb': float(parts[1]) if parts[1].replace('.', '', 1).isdigit() else None,
                    'driver': parts[2] if len(parts) > 2 else None,
                    'power_limit_w': float(parts[3]) if len(parts) > 3 and parts[3].replace('.', '', 1).isdigit() else None,
                    'vendor': 'nvidia', 'source': 'nvidia-smi',
                    'observed_at': utcnow(),
                })
    pci = _run(['lspci', '-mm'])
    if pci:
        for line in pci.splitlines():
            if re.search(r'VGA|3D controller|Display controller', line, re.I):
                m = re.search(r'"([^"]+)"', line)
                name = m.group(1) if m else line.strip()[:80]
                vendor = ('nvidia' if re.search(r'nvidia', line, re.I) else
                          'amd' if re.search(r'amd|ati|radeon', line, re.I) else
                          'intel' if re.search(r'intel', line, re.I) else 'unknown')
                # Skip lspci duplicates of nvidia-smi rows (same vendor+name fragment).
                if vendor == 'nvidia' and any(re.sub(r'\W', '', name).lower()[:12]
                                              in re.sub(r'\W', '', g['name']).lower()
                                              for g in gpus):
                    continue
                gpus.append({'name': name, 'memory_mb': None, 'driver': None,
                             'power_limit_w': None, 'vendor': vendor,
                             'source': 'lspci (no VRAM/driver without vendor smi)',
                             'observed_at': utcnow()})
    return gpus


def detect_disks():
    """Usable disk on / only. Full storage inventory is future (powparts)."""
    out = {'root_total_gb': None, 'sources': [], 'observed_at': utcnow()}
    try:
        total, _, _ = shutil.disk_usage('/')
        out['root_total_gb'] = round(total / 10**9, 1)
        out['sources'].append('shutil.disk_usage(/)')
    except OSError:
        pass
    return out


def inventory(electricity=ELECTRICITY_DEFAULT):
    """Full local inventory + stable fingerprint. Never raises."""
    cpu = detect_cpu()
    memory = detect_memory()
    gpus = detect_gpus()
    disks = detect_disks()
    ident = {
        'cpu_model': cpu.get('model'),
        'cpu_threads': cpu.get('threads'),
        'memory_gb': memory.get('total_gb'),
        'gpus': sorted(g.get('name', '') for g in gpus),
        'disk_gb': disks.get('root_total_gb'),
    }
    fp = hashlib.sha256(
        json.dumps(ident, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return {
        'fingerprint': fp,
        'cpu': cpu, 'memory': memory, 'gpus': gpus, 'disks': disks,
        'electricity_usd_kwh': electricity,
        'observed_at': utcnow(),
    }


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def match_archetypes(inv, registry=None):
    """Match detected components to V1_HARDWARE archetypes.

    Returns [(archetype, coin, specs, detected_name)]. Substring match
    on normalized names either direction; unmatched components disclosed
    by the caller, never force-fit.
    """
    if registry is None:
        from v1_live_cards import V1_HARDWARE  # noqa: E402  (lazy: mcp import order)
        registry = V1_HARDWARE
    detected = []
    if inv.get('cpu', {}).get('model'):
        detected.append(('cpu', inv['cpu']['model']))
    for g in inv.get('gpus', []):
        if g.get('name'):
            detected.append(('gpu', g['name']))
    matches = []
    for coin, hwmap in (registry or {}).items():
        for arch, specs in (hwmap or {}).items():
            an = _norm(arch)
            for kind, name in detected:
                dn = _norm(name)
                if an and dn and (an in dn or dn in an):
                    matches.append({'archetype': arch, 'coin': coin,
                                    'specs': specs, 'detected_as': name,
                                    'detected_kind': kind})
    return matches


def _latest_opportunity():
    """Latest opportunity_snapshot row per hardware archetype."""
    best = {}
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'opportunity_snapshot',
            'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                hw = r.get('hardware', '')
                stamp = r.get('generated_at') or r.get('date', '')
                if hw and (hw not in best or stamp > best[hw][0]):
                    best[hw] = (stamp, r)
    return {k: v[1] for k, v in best.items()}


def rank_routes(routes):
    """Best-first by net, None-nets last. Pure helper (tested)."""
    return sorted(routes or [],
                  key=lambda r: (r.get('net_profit_usd_day')
                                 if r.get('net_profit_usd_day') is not None
                                 else float('-inf')),
                  reverse=True)


def recommend(inv=None, date=None, electricity=ELECTRICITY_DEFAULT):
    """Join inventory to the prediction log. Read-only; no execution.

    Returns report with per-archetype best_action + full ranked routes,
    unmatched components disclosed, and the prediction hashes so a later
    outcome row can join expected vs realized.
    """
    inv = inv or inventory(electricity=electricity)
    elec = inv.get('electricity_usd_kwh', electricity)
    opps = _latest_opportunity()
    if date:
        dated = {}
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', 'opportunity_snapshot',
                'chain=*', f'date={date}', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if r.get('hardware'):
                        dated[r['hardware']] = r
        if dated:
            opps = dated
    matches = match_archetypes(inv)
    matched_archs = sorted({m['archetype'] for m in matches})
    recs = []
    for arch in matched_archs:
        row = opps.get(arch)
        if not row:
            recs.append({'hardware': arch, 'status': 'no snapshot yet',
                         'note': 'run scripts/snapshot_opportunity.py first',
                         'matched_as': sorted({m['detected_as'] for m in matches
                                               if m['archetype'] == arch})})
            continue
        routes = rank_routes(row.get('routes'))
        recs.append({'hardware': arch,
                     'matched_as': sorted({m['detected_as'] for m in matches
                                           if m['archetype'] == arch}),
                     'date': row.get('date'),
                     'best_action': row.get('best_action'),
                     'routes': routes,
                     'prediction_hash': row.get('prediction_hash'),
                     'model_version': row.get('model_version')})
    # Components with no registry benchmark: disclose, don't fabricate.
    matched_names = {_norm(m['detected_as']) for m in matches}
    unmatched = []
    if inv.get('cpu', {}).get('model') and _norm(inv['cpu']['model']) not in matched_names:
        unmatched.append({'kind': 'cpu', 'name': inv['cpu']['model'],
                          'note': 'no measured benchmark in registry'})
    for g in inv.get('gpus', []):
        if g.get('name') and _norm(g['name']) not in matched_names:
            unmatched.append({'kind': 'gpu', 'name': g['name'],
                              'note': 'no measured benchmark in registry'})
    return {
        'fingerprint': inv.get('fingerprint'),
        'inventory': inv,
        'electricity_usd_kwh': elec,
        'recommendations': recs,
        'unmatched': unmatched,
        'opportunity_coverage': f'{len([r for r in recs if r.get("best_action")])}/{len(recs)} archetypes with snapshots',
        'generated_at': utcnow(),
    }
