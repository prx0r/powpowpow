"""
PowPowPow Master Daemon
Runs collectors continuously with supervision, schedules normalization,
serves API. UTC-only. Writes daemon.pid for health checks.
"""

import os
import sys
import time
import json
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from warehouse import store_normalized  # shim over core

CONFIG = {
    'collection_interval': 300,
    'normalization_interval': 60,
    'api_port': 5000,
    # Supervised one-shot collectors (run to completion, daemon restarts on interval).
    # L2 archival + API are long-lived.
    'collectors': [
        'collectors/qubic_collector.py',
        'collectors/prl_collector.py',
        'collectors/xmr_collector.py',
        'collectors/clore_collector.py',
    ],
}

PID_FILE = os.path.join(BASE_DIR, 'daemon.pid')


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class PowPowPowDaemon:
    def __init__(self):
        self.running = False
        self.processes = {}
        self.last_collector_run = 0.0
        self.last_normalization = 0.0
        self.stats = {'started_at': None, 'cycles': 0, 'errors': 0,
                      'last_collection': None, 'last_normalization': None}

    def start(self):
        print(f"\n{'='*60}")
        print(f"PowPowPow Daemon Starting — {utcnow()}")
        print(f"{'='*60}")
        self.running = True
        self.stats['started_at'] = utcnow()
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        self.start_api()
        self.start_l2_archival()
        self.run_collectors()  # first pass now
        self.normalize_data()  # first pass now
        print("\n[RUNNING] All components started")
        print(f"[PID] {os.getpid()}")
        try:
            while self.running:
                time.sleep(1)
                self.stats['cycles'] += 1
                now = time.time()
                if now - self.last_collector_run >= CONFIG['collection_interval']:
                    self.run_collectors()
                if now - self.last_normalization >= CONFIG['normalization_interval']:
                    self.normalize_data()
                self.supervise()
                if self.stats['cycles'] % 300 == 0:
                    self.print_status()
        except KeyboardInterrupt:
            self.stop()

    def _spawn(self, name, script, long_lived=False):
        try:
            proc = subprocess.Popen([sys.executable, os.path.join(BASE_DIR, script)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes[name] = {'proc': proc, 'script': script, 'long_lived': long_lived,
                                    'started': time.time()}
            print(f"  ✓ {name} ({script}) pid={proc.pid}")
        except Exception as e:
            self.stats['errors'] += 1
            print(f"  ✗ {name} failed to start: {e}")

    def run_collectors(self):
        """Run one-shot collectors (each runs to completion)."""
        print("[COLLECTORS] Running supervised pass...")
        for script in CONFIG['collectors']:
            name = os.path.splitext(os.path.basename(script))[0]
            self._spawn(name, script)
        self.last_collector_run = time.time()
        self.stats['last_collection'] = utcnow()

    def start_l2_archival(self):
        print("[STARTING] L2 archival (long-lived)...")
        self._spawn('l2', 'collectors/l2_archival.py', long_lived=True)

    def start_api(self):
        print("[STARTING] API server (long-lived)...")
        self._spawn('api', 'api.py', long_lived=True)
        print(f"  ✓ API on port {CONFIG['api_port']}")

    def supervise(self):
        """Restart crashed long-lived processes; reap finished one-shots."""
        for name, info in list(self.processes.items()):
            proc = info['proc']
            ret = proc.poll()
            if ret is None:
                continue
            if info['long_lived']:
                print(f"[SUPERVISE] {name} exited ({ret}) — restarting...")
                self._spawn(name, info['script'], long_lived=True)
            else:
                if ret != 0:
                    self.stats['errors'] += 1
                    try:
                        err = (proc.stderr.read() or b'')[-2000:].decode('utf-8', 'replace')
                        if err.strip():
                            print(f"[COLLECTOR {name}] stderr tail: {err.strip()[-500:]}")
                    except Exception:
                        pass
                del self.processes[name]

    def normalize_data(self):
        """Normalization is handled inside collectors via core.store_normalized.
        This pass only records the heartbeat so the 90-day factor clock is visible."""
        try:
            self.last_normalization = time.time()
            self.stats['last_normalization'] = utcnow()
        except Exception:
            self.stats['errors'] += 1

    def print_status(self):
        try:
            started = datetime.fromisoformat(self.stats['started_at'])
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        except Exception:
            elapsed = 0
        print(f"\n[STATUS] Uptime: {elapsed/3600:.1f}h | Cycles: {self.stats['cycles']} | "
              f"Errors: {self.stats['errors']} | procs: {len(self.processes)}")
        for name, info in self.processes.items():
            status = "running" if info['proc'].poll() is None else "exited"
            print(f"  {name}: {status}")

    def stop(self):
        print("\n[STOPPING] Daemon...")
        self.running = False
        for name, info in self.processes.items():
            proc = info['proc']
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  ✓ Stopped {name}")
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
                print(f"  ✓ Killed {name}")
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass
        print("[STOPPED] Daemon stopped")


def run_daemon():
    daemon = PowPowPowDaemon()

    def signal_handler(sig, frame):
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    daemon.start()


if __name__ == '__main__':
    run_daemon()
