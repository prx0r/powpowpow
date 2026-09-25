"""Remove test-written artifacts from the live warehouse.

Test fixtures used to patch the `core` package namespace instead of the
underlying `core.py` module globals, so observations went into the live
warehouse. The fixture is fixed; this clears what it already produced.

    python3 scripts/purge_test_artifacts.py --dry-run
    python3 scripts/purge_test_artifacts.py
"""

import argparse
import glob
import json
import os
import tempfile


def purge_trade_rows(apply):
    removed = 0
    for path in glob.glob("warehouse/normalized/trade/chain=*/date=*/hour=*.jsonl"):
        with open(path) as handle:
            lines = handle.readlines()
        kept = [line for line in lines if _symbol(line) != "X"]
        dropped = len(lines) - len(kept)
        if not dropped or not apply:
            removed += dropped
            continue
        directory = os.path.dirname(path)
        descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".purge")
        with os.fdopen(descriptor, "w") as handle:
            handle.writelines(kept)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        removed += dropped
    return removed


def _symbol(line):
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row.get("symbol") if isinstance(row, dict) else None


def purge_test_raw(apply):
    removed = 0
    for chain in sorted(os.listdir("warehouse/raw")):
        for path in glob.glob(f"warehouse/raw/{chain}/*.json"):
            try:
                with open(path) as handle:
                    envelope = json.load(handle)
            except (OSError, ValueError):
                continue
            if envelope.get("endpoint") != "https://x":
                continue
            removed += 1
            if apply:
                os.unlink(path)
    return removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    apply = not args.dry_run
    trades = purge_trade_rows(apply)
    raw = purge_test_raw(apply)
    verb = "would remove" if not apply else "removed"
    print(
        f"{verb}: {trades} trade rows with symbol=X, {raw} raw envelopes "
        f"with endpoint=https://x"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
