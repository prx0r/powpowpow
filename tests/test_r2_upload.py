import base64
import hashlib
import json
import os
import threading
import time

from botocore.exceptions import ClientError

from scripts.r2_upload import R2Sync, upload_lock, write_state


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.put_calls = 0
        self.copy_calls = 0
        self.lock = threading.Lock()

    def head_object(self, Bucket, Key):
        with self.lock:
            if Key not in self.objects:
                raise ClientError(
                    {"Error": {"Code": "404", "Message": "Not Found"}},
                    "HeadObject",
                )
            body, metadata = self.objects[Key]
        return {
            "ContentLength": len(body),
            "ETag": f'"{hashlib.md5(body, usedforsecurity=False).hexdigest()}"',
            "Metadata": metadata,
        }

    def put_object(
        self, Bucket, Key, Body, ContentLength, ContentMD5, ContentType, Metadata
    ):
        with self.lock:
            self.put_calls += 1
            assert ContentLength == len(Body)
            assert (
                base64.b64decode(ContentMD5)
                == hashlib.md5(Body, usedforsecurity=False).digest()
            )
            self.objects[Key] = (Body, Metadata)

    def copy_object(
        self, Bucket, Key, CopySource, ContentType, Metadata, MetadataDirective
    ):
        with self.lock:
            self.copy_calls += 1
            assert MetadataDirective == "REPLACE"
            body, _ = self.objects[Key]
            self.objects[Key] = (body, Metadata)


def make_old(path, seconds=7200):
    timestamp = time.time() - seconds
    os.utime(path, (timestamp, timestamp))


def test_upload_lock_accepts_string_path(tmp_path):
    lock = tmp_path / "sync.lock"
    with upload_lock(str(lock)):
        assert lock.exists()


def test_r2_sync_uploads_verifies_and_skips(tmp_path):
    local = tmp_path / "warehouse"
    path = local / "raw" / "safetrade" / "one.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"id":1}\n')
    s3 = FakeS3()
    state = tmp_path / "state.json"
    sync = R2Sync(
        s3=s3,
        bucket="bucket",
        prefix="powpowpow",
        state_path=state,
        retention={},
    )

    first = sync.run(local)
    second = sync.run(local)

    assert first["uploaded"] == 1
    assert second["skipped"] == 1
    assert s3.put_calls == 1
    saved = json.loads(state.read_text())
    key = "powpowpow/raw/safetrade/one.json"
    assert saved[key]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_r2_sync_reuses_byte_identical_remote_object(tmp_path):
    local = tmp_path / "warehouse"
    path = local / "raw" / "safetrade" / "same.json"
    path.parent.mkdir(parents=True)
    body = b'{"id":4}\n'
    path.write_bytes(body)
    s3 = FakeS3()
    s3.objects["powpowpow/raw/safetrade/same.json"] = (body, {})
    sync = R2Sync(
        s3=s3,
        bucket="bucket",
        prefix="powpowpow",
        state_path=tmp_path / "state.json",
        retention={},
    )

    summary = sync.run(local)

    assert summary["verified"] == 1
    assert s3.put_calls == 0
    assert s3.copy_calls == 1
    assert s3.objects["powpowpow/raw/safetrade/same.json"][1] == {
        "sha256": hashlib.sha256(body).hexdigest()
    }


def test_r2_sync_workers_upload_concurrently(tmp_path):
    local = tmp_path / "warehouse"
    for index in range(12):
        path = local / "raw" / "safetrade" / f"file-{index}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'{{"id":{index}}}\n')
    s3 = FakeS3()
    sync = R2Sync(
        s3=s3,
        bucket="bucket",
        prefix="powpowpow",
        state_path=tmp_path / "state.json",
        retention={},
        workers=4,
    )

    summary = sync.run(local)

    assert summary["uploaded"] == 12
    assert summary["failed"] == 0
    assert s3.put_calls == 12


def test_r2_sync_deletes_only_after_remote_verification(tmp_path):
    local = tmp_path / "warehouse"
    path = local / "raw" / "safetrade" / "old.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"id":2}\n')
    make_old(path)
    s3 = FakeS3()
    sync = R2Sync(
        s3=s3,
        bucket="bucket",
        prefix="powpowpow",
        state_path=tmp_path / "state.json",
        retention={"raw": 3600},
    )

    summary = sync.run(local)

    assert summary["uploaded"] == 1
    assert summary["deleted"] == 1
    assert not path.exists()
    assert "powpowpow/raw/safetrade/old.json" in s3.objects


def test_r2_sync_keeps_local_file_when_upload_fails(tmp_path):
    class FailingS3(FakeS3):
        def put_object(self, **kwargs):
            raise RuntimeError("upload failed")

    local = tmp_path / "warehouse"
    path = local / "raw" / "safetrade" / "keep.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"id":3}\n')
    make_old(path)
    sync = R2Sync(
        s3=FailingS3(),
        bucket="bucket",
        prefix="powpowpow",
        state_path=tmp_path / "state.json",
        retention={"raw": 3600},
    )

    summary = sync.run(local)

    assert summary["failed"] == 1
    assert summary["deleted"] == 0
    assert path.exists()


def test_prune_deletes_only_verified_old_files(tmp_path):
    local = tmp_path / "warehouse"
    verified_old = local / "raw" / "safetrade" / "old.json"
    young = local / "raw" / "safetrade" / "young.json"
    unknown = local / "raw" / "safetrade" / "unknown.json"
    for path in (verified_old, young, unknown):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"id":1}\n')
    make_old(verified_old)

    s3 = FakeS3()
    body = verified_old.read_bytes()
    s3.objects["powpowpow/raw/safetrade/old.json"] = (
        body,
        {"sha256": hashlib.sha256(body).hexdigest()},
    )
    write_state(
        str(tmp_path / "state.json"),
        {
            "powpowpow/raw/safetrade/old.json": {
                "signature": [len(body), verified_old.stat().st_mtime_ns],
                "sha256": hashlib.sha256(body).hexdigest(),
                "verified_at": time.time(),
            },
            "powpowpow/raw/safetrade/young.json": {
                "signature": [young.stat().st_size, young.stat().st_mtime_ns],
                "sha256": "unused",
                "verified_at": time.time(),
            },
        },
    )

    sync = R2Sync(
        s3=s3,
        bucket="bucket",
        prefix="powpowpow",
        state_path=tmp_path / "state.json",
        retention={"raw": 3600},
    )
    summary = sync.prune(local)

    assert summary["deleted"] == 1
    assert summary["failed"] == 0
    assert not verified_old.exists()
    assert young.exists()
    assert unknown.exists()


def test_prune_keeps_file_when_remote_is_missing(tmp_path):
    local = tmp_path / "warehouse"
    path = local / "raw" / "safetrade" / "gone.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"id":2}\n')
    make_old(path)

    s3 = FakeS3()
    sync = R2Sync(
        s3=s3,
        bucket="bucket",
        prefix="powpowpow",
        state_path=tmp_path / "state.json",
        retention={"raw": 3600},
    )
    # state claims the file is uploaded, but the object is absent
    write_state(
        str(tmp_path / "state.json"),
        {
            "powpowpow/raw/safetrade/gone.json": {
                "signature": [path.stat().st_size, path.stat().st_mtime_ns],
                "sha256": "bogus",
                "verified_at": time.time(),
            }
        },
    )

    summary = sync.prune(local)

    assert summary["deleted"] == 0
    assert summary["failed"] == 1
    assert path.exists()
