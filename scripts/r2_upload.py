#!/usr/bin/env python3
"""Upload powpowpow warehouse to Cloudflare R2.

Usage:
    python3 r2_upload.py [--dir warehouse] [--remote powpowpow] [--dry-run]

Setup:
    1. Create R2 bucket in Cloudflare dashboard
    2. Create R2 API token with Object Read & Write permissions
    3. Set env vars:
        export CF_R2_TOKEN=your_r2_api_token
        export CF_ACCOUNT_ID=your_account_id
        export R2_BUCKET=powpowpow-warehouse
"""

import argparse
import hashlib
import hmac
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)


def r2_sign(method, resource, date, content_type="", access_key="", secret_key="", account_id="", body_hash=""):
    """AWS Signature V4 for Cloudflare R2."""
    date_str = date.strftime("%Y%m%dT%H%M%SZ")
    date_short = date.strftime("%Y%m%d")
    
    if not body_hash:
        body_hash = hashlib.sha256(b"").hexdigest()
    
    # Canonical request
    canonical_uri = quote(resource, safe="/")
    canonical_headers = f"content-type:{content_type}\ndate:{date_str}\nhost:{account_id}.r2.cloudflarestorage.com\nx-amz-content-sha256:{body_hash}\n"
    signed_headers = "content-type;date;host;x-amz-content-sha256"
    
    canonical_request = f"{method}\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{body_hash}"
    
    # String to sign
    credential_scope = f"{date_short}/auto/s3/aws4_request"
    string_to_sign = f"AWS4-HMAC-SHA256\n{date_str}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    
    # Signing key
    def hmac_sha256(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()
    
    k_date = hmac_sha256(f"AWS4{secret_key}".encode(), date_short)
    k_region = hmac_sha256(k_date, "auto")
    k_service = hmac_sha256(k_region, "s3")
    k_signing = hmac_sha256(k_service, "aws4_request")
    
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
    
    return f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"


def upload_file(local_path, remote_key, bucket, account_id, access_key, secret_key, dry_run=False):
    """Upload a single file to R2."""
    content_type = {
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".parquet": "application/octet-stream",
    }.get(local_path.suffix, "application/octet-stream")
    
    file_size = local_path.stat().st_size
    
    if dry_run:
        print(f"  [DRY] {remote_key} ({file_size:,} bytes)")
        return True
    
    # Read file and compute body hash
    body = local_path.read_bytes()
    body_hash = hashlib.sha256(body).hexdigest()
    
    date = datetime.now(timezone.utc)
    resource = f"/{bucket}/{remote_key}"
    auth = r2_sign("PUT", resource, date, content_type, access_key, secret_key, account_id, body_hash)
    
    headers = {
        "Content-Type": content_type,
        "Date": date.strftime("%Y%m%dT%H%M%SZ"),
        "Authorization": auth,
        "x-amz-content-sha256": body_hash,
    }
    
    resp = requests.put(
        f"https://{account_id}.r2.cloudflarestorage.com{resource}",
        headers=headers,
        data=body,
        timeout=60,
    )
    
    if resp.status_code in (200, 201):
        print(f"  OK {remote_key} ({file_size:,} bytes)")
        return True
    else:
        print(f"  FAIL {remote_key}: {resp.status_code} {resp.text[:200]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Upload warehouse to R2")
    parser.add_argument("--dir", default="warehouse", help="Local directory")
    parser.add_argument("--remote", default="powpowpow", help="Remote prefix")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--older-than", type=int, default=0, help="Only files older than N days")
    args = parser.parse_args()
    
    access_key = os.environ.get("CF_R2_ACCESS_KEY")
    secret_key = os.environ.get("CF_R2_SECRET_KEY")
    account_id = os.environ.get("CF_ACCOUNT_ID")
    bucket = args.bucket or os.environ.get("R2_BUCKET", "powpowpow-warehouse")
    
    if not access_key or not secret_key or not account_id:
        print("Error: Set CF_R2_ACCESS_KEY, CF_R2_SECRET_KEY, and CF_ACCOUNT_ID environment variables")
        sys.exit(1)
    
    local_dir = Path(args.dir)
    if not local_dir.exists():
        print(f"Error: {local_dir} does not exist")
        sys.exit(1)
    
    # Find files
    extensions = {".json", ".jsonl", ".parquet"}
    files = []
    for f in local_dir.rglob("*"):
        if f.is_file() and f.suffix in extensions and ".tmp" not in f.name and ".lock" not in f.name:
            if args.older_than > 0:
                age_days = (time.time() - f.stat().st_mtime) / 86400
                if age_days < args.older_than:
                    continue
            files.append(f)
    
    if not files:
        print("No files to upload")
        return
    
    print(f"Found {len(files)} files to upload")
    
    # Upload
    success = 0
    failed = 0
    for f in sorted(files):
        relative = f.relative_to(local_dir)
        remote_key = f"{args.remote}/{relative}"
        if upload_file(f, remote_key, bucket, account_id, access_key, secret_key, args.dry_run):
            success += 1
        else:
            failed += 1
    
    print(f"\nDone: {success} uploaded, {failed} failed")


if __name__ == "__main__":
    main()
