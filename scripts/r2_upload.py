#!/usr/bin/env python3

import argparse
import base64
import fcntl
import hashlib
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("Error: boto3 is required", file=sys.stderr)
    sys.exit(1)

EXTENSIONS = {".json", ".jsonl", ".parquet"}
CONTENT_TYPES = {
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".parquet": "application/octet-stream",
}


def content_type(path):
    return CONTENT_TYPES.get(path.suffix, "application/octet-stream")


def remote_key(prefix, path):
    return f"{prefix.strip('/')}/{path.as_posix()}"


def parse_retention(values):
    result = {}
    for value in values:
        try:
            prefix, hours = value.split("=", 1)
            retention = float(hours) * 3600
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"invalid retention '{value}', expected PREFIX=HOURS"
            ) from exc
        if not prefix or retention < 0:
            raise argparse.ArgumentTypeError(
                f"invalid retention '{value}', expected PREFIX=HOURS"
            )
        result[prefix.strip("/")] = retention
    return result


def load_state(path):
    path = Path(path).expanduser()
    try:
        value = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot load state {path}: {exc}") from exc
    return value if isinstance(value, dict) else {}


def write_state(path, state):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump(state, handle, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


@contextmanager
def upload_lock(path):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another R2 sync is already running") from None
        yield
    finally:
        os.close(descriptor)


def missing_remote(exc):
    if not isinstance(exc, ClientError):
        return False
    code = str(exc.response.get("Error", {}).get("Code", ""))
    status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in {"404", "NoSuchKey", "NotFound"} or status == 404


def stable_read(path):
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        body = handle.read()
        after = os.fstat(handle.fileno())
    before_signature = [before.st_size, before.st_mtime_ns]
    after_signature = [after.st_size, after.st_mtime_ns]
    if before_signature != after_signature:
        return None, None, None, None
    sha256 = hashlib.sha256(body).hexdigest()
    md5 = hashlib.md5(body, usedforsecurity=False).digest()
    return body, sha256, md5, after_signature


def matches_remote(head, size, sha256):
    if head is None:
        return False
    metadata = head.get("Metadata", {})
    return (
        int(head.get("ContentLength", -1)) == size and metadata.get("sha256") == sha256
    )


class R2Sync:
    def __init__(
        self,
        s3,
        bucket,
        prefix,
        state_path,
        retention,
        min_age_seconds=0,
        recheck_seconds=86400,
        verbose=False,
        workers=1,
    ):
        self.s3 = s3
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.state_path = Path(state_path).expanduser()
        self.retention = retention
        self.min_age_seconds = min_age_seconds
        self.recheck_seconds = recheck_seconds
        self.verbose = verbose
        self.workers = max(1, int(workers))

    def head(self, key):
        try:
            return self.s3.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if missing_remote(exc):
                return None
            raise

    def copy_metadata(self, path, key, body, sha256):
        self.s3.copy_object(
            Bucket=self.bucket,
            Key=key,
            CopySource={"Bucket": self.bucket, "Key": key},
            ContentType=content_type(path),
            Metadata={"sha256": sha256},
            MetadataDirective="REPLACE",
        )
        head = self.head(key)
        if not matches_remote(head, len(body), sha256):
            raise RuntimeError("remote verification failed")

    def put(self, path, key, body, sha256, md5):
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentLength=len(body),
            ContentMD5=base64.b64encode(md5).decode(),
            ContentType=content_type(path),
            Metadata={"sha256": sha256},
        )
        head = self.head(key)
        if not matches_remote(head, len(body), sha256):
            raise RuntimeError("remote verification failed")

    def ensure_remote(self, path, key, prior, force_check, now):
        current = path.stat()
        signature = [current.st_size, current.st_mtime_ns]
        if (
            prior
            and prior.get("signature") == signature
            and not force_check
            and now - float(prior.get("verified_at", 0)) < self.recheck_seconds
        ):
            return prior, "skipped"

        body, sha256, md5, signature = stable_read(path)
        if body is None:
            return None, "deferred"

        head = self.head(key)
        if matches_remote(head, len(body), sha256):
            status = "verified"
        elif (
            head is not None
            and int(head.get("ContentLength", -1)) == len(body)
            and head.get("ETag", "").strip('"') == md5.hex()
            and not head.get("Metadata", {}).get("sha256")
        ):
            self.copy_metadata(path, key, body, sha256)
            status = "verified"
        else:
            self.put(path, key, body, sha256, md5)
            status = "uploaded"

        return {
            "signature": signature,
            "sha256": sha256,
            "verified_at": now,
        }, status

    def run(self, local_dir):
        local_dir = Path(local_dir).expanduser().resolve()
        now = time.time()
        state = load_state(self.state_path)
        working = dict(state)
        summary = {
            "eligible": 0,
            "uploaded": 0,
            "verified": 0,
            "skipped": 0,
            "deferred": 0,
            "deleted": 0,
            "failed": 0,
        }

        def scan():
            found = []
            for path in local_dir.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix not in EXTENSIONS:
                    continue
                if ".tmp" in path.name or ".lock" in path.name:
                    continue
                found.append(path)
            return found

        def process(path):
            try:
                age = now - path.stat().st_mtime
                relative = path.relative_to(local_dir)
                key = remote_key(self.prefix, relative)
                if age < self.min_age_seconds:
                    return (str(path), key, None, "skipped_young", False, None)
                retention = self.retention.get(relative.parts[0])
                force_check = retention is not None and age >= retention
                entry, status = self.ensure_remote(
                    path,
                    key,
                    state.get(key),
                    force_check,
                    now,
                )
                deleted = False
                if force_check and entry is not None:
                    latest = path.stat()
                    latest_signature = [latest.st_size, latest.st_mtime_ns]
                    if latest_signature != entry["signature"]:
                        raise RuntimeError("file changed before delete")
                    head = self.head(key)
                    if not matches_remote(head, latest.st_size, entry["sha256"]):
                        raise RuntimeError("pre-delete verification failed")
                    path.unlink()
                    deleted = True
                return (str(path), key, entry, status, deleted, None)
            except (
                BotoCoreError,
                ClientError,
                OSError,
                RuntimeError,
                ValueError,
            ) as exc:
                try:
                    relative = path.relative_to(local_dir)
                    key = remote_key(self.prefix, relative)
                except ValueError:
                    key = None
                return (
                    str(path),
                    key,
                    None,
                    "failed",
                    False,
                    f"{type(exc).__name__}: {exc}",
                )

        attempted = set()
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for pass_index in range(2):
                pending = []
                for path in sorted(scan()):
                    try:
                        key = remote_key(self.prefix, path.relative_to(local_dir))
                    except ValueError:
                        continue
                    if key in attempted:
                        continue
                    attempted.add(key)
                    pending.append(path)
                if not pending:
                    break
                if pass_index:
                    print(
                        f"rescan: {len(pending)} files created during pass 1",
                        flush=True,
                    )
                since_flush = 0
                for result in executor.map(process, pending):
                    if result is None:
                        continue
                    path_name, key, entry, status, deleted, error = result
                    if status == "failed":
                        summary["failed"] += 1
                        if key:
                            working.pop(key, None)
                        print(f"  FAIL {path_name}: {error}", file=sys.stderr)
                    elif status == "skipped_young":
                        if key:
                            attempted.discard(key)
                        continue
                    else:
                        summary["eligible"] += 1
                        if status == "deferred":
                            summary["deferred"] += 1
                            if key:
                                working.pop(key, None)
                        else:
                            summary[status] += 1
                            if key:
                                working[key] = entry
                        if deleted:
                            summary["deleted"] += 1
                    since_flush += 1
                    if since_flush >= 1000:
                        write_state(self.state_path, working)
                        print(
                            f"progress eligible={summary['eligible']} "
                            f"uploaded={summary['uploaded']} "
                            f"verified={summary['verified']} "
                            f"failed={summary['failed']}",
                            flush=True,
                        )
                        since_flush = 0

        write_state(self.state_path, working)
        return summary

    def prune(self, local_dir):
        """Retention only: delete local files already verified remote.

        Deliberately separate from `run()` so local disk keeps shrinking even
        when the uploader is OOM-killed or otherwise failing. A file is only
        removed if this run has a state entry for it AND a fresh remote HEAD
        confirms size and SHA-256.
        """
        local_dir = Path(local_dir).expanduser().resolve()
        now = time.time()
        state = load_state(self.state_path)
        summary = {"eligible": 0, "deleted": 0, "kept": 0, "failed": 0}

        paths = []
        for path in local_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in EXTENSIONS:
                continue
            if ".tmp" in path.name or ".lock" in path.name:
                continue
            paths.append(path)

        def consider(path):
            try:
                relative = path.relative_to(local_dir)
            except ValueError:
                return None, None, None
            key = remote_key(self.prefix, relative)
            entry = state.get(key)
            if entry is None:
                return key, "kept", "never verified remote"
            age = now - path.stat().st_mtime
            retention = self.retention.get(relative.parts[0])
            if retention is None or age < retention:
                return key, "kept", None
            try:
                size = entry["signature"][0]
                sha256 = entry["sha256"]
                head = self.head(key)
                if not matches_remote(head, size, sha256):
                    return key, "failed", "pre-delete verification failed"
                latest = path.stat()
                if [latest.st_size, latest.st_mtime_ns] != entry["signature"]:
                    return key, "failed", "file changed before delete"
                path.unlink()
                return key, "deleted", None
            except (BotoCoreError, ClientError, OSError) as exc:
                return key, "failed", f"{type(exc).__name__}: {exc}"

        with ThreadPoolExecutor(max_workers=min(self.workers, 4)) as executor:
            for key, status, reason in executor.map(consider, paths):
                if key is None:
                    continue
                if status == "failed":
                    summary["failed"] += 1
                    print(f"  KEEP {key}: {reason}", file=sys.stderr)
                elif status == "deleted":
                    summary["deleted"] += 1
                    state.pop(key, None)
                else:
                    summary["kept"] += 1

        write_state(self.state_path, state)
        return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="warehouse")
    parser.add_argument("--remote", default="powpowpow")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--older-than", type=float, default=0)
    parser.add_argument("--min-age-minutes", type=float, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--prune",
        action="store_true",
        help="retention only: verify then delete, no uploads",
    )
    parser.add_argument(
        "--retention-hours",
        action="append",
        default=[],
        metavar="PREFIX=HOURS",
    )
    parser.add_argument(
        "--state-file",
        default="~/.local/state/powpowpow/r2-sync.json",
    )
    parser.add_argument(
        "--lock-file",
        default="~/.local/state/powpowpow/r2-sync.lock",
    )
    args = parser.parse_args()

    local_dir = Path(args.dir).expanduser().resolve()
    if not local_dir.is_dir():
        print(f"Error: {local_dir} does not exist", file=sys.stderr)
        return 2

    state_path = Path(args.state_file).expanduser().resolve()
    lock_path = Path(args.lock_file).expanduser().resolve()
    for name, path in (("state", state_path), ("lock", lock_path)):
        if path == local_dir or local_dir in path.parents:
            parser.error(f"{name} file must be outside --dir")

    retention = parse_retention(args.retention_hours)
    min_age_seconds = max(
        args.min_age_minutes * 60,
        args.older_than * 86400,
    )

    if args.dry_run:
        now = time.time()
        eligible = 0
        total_bytes = 0
        for path in local_dir.rglob("*"):
            if (
                path.is_file()
                and path.suffix in EXTENSIONS
                and ".tmp" not in path.name
                and ".lock" not in path.name
                and now - path.stat().st_mtime >= min_age_seconds
            ):
                eligible += 1
                total_bytes += path.stat().st_size
        print(f"eligible={eligible} bytes={total_bytes}")
        return 0

    access_key = os.environ.get("CF_R2_ACCESS_KEY")
    secret_key = os.environ.get("CF_R2_SECRET_KEY")
    account_id = os.environ.get("CF_ACCOUNT_ID")
    if not access_key or not secret_key or not account_id:
        print(
            "Error: set CF_R2_ACCESS_KEY, CF_R2_SECRET_KEY, and CF_ACCOUNT_ID",
            file=sys.stderr,
        )
        return 2

    endpoint = (
        args.endpoint
        or os.environ.get("CLOUDFLARE_R2_ENDPOINT")
        or f"https://{account_id}.r2.cloudflarestorage.com"
    )
    bucket = args.bucket or os.environ.get("R2_BUCKET", "powpowpow-warehouse")
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(
            retries={"max_attempts": 5, "mode": "adaptive"},
            connect_timeout=15,
            read_timeout=60,
        ),
    )

    sync = R2Sync(
        s3=s3,
        bucket=bucket,
        prefix=args.remote,
        state_path=state_path,
        retention=retention,
        min_age_seconds=min_age_seconds,
        verbose=args.verbose,
        workers=args.workers,
    )

    try:
        with upload_lock(lock_path):
            summary = sync.prune(local_dir) if args.prune else sync.run(local_dir)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(" ".join(f"{key}={value}" for key, value in summary.items()))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
