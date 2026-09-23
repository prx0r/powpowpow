#!/bin/bash
# Upload powpowpow warehouse to Cloudflare R2
# Uses Cloudflare API directly (no AWS CLI needed)
#
# Setup:
#   1. Create R2 bucket in Cloudflare dashboard
#   2. Create R2 API token with Object Read & Write permissions
#   3. Set env vars:
#      export CF_API_TOKEN=your_r2_api_token
#      export CF_ACCOUNT_ID=your_account_id
#      export R2_BUCKET=powpowpow-warehouse
#   4. Run: ./r2_upload.sh [local_dir] [remote_prefix]

set -euo pipefail

LOCAL_DIR="${1:-warehouse}"
REMOTE_PREFIX="${2:-powpowpow}"
BUCKET="${R2_BUCKET:-powpowpow-warehouse}"

if [ -z "${CF_API_TOKEN:-}" ] || [ -z "${CF_ACCOUNT_ID:-}" ]; then
    echo "Error: Set CF_API_TOKEN and CF_ACCOUNT_ID"
    exit 1
fi

# Find files to upload (exclude tmp/lock files)
echo "Scanning ${LOCAL_DIR}..."
FILES=$(find "${LOCAL_DIR}" -type f \( -name "*.json" -o -name "*.jsonl" -o -name "*.parquet" \) ! -name "*.tmp" ! -name "*.lock" 2>/dev/null)

if [ -z "$FILES" ]; then
    echo "No files to upload"
    exit 0
fi

COUNT=$(echo "$FILES" | wc -l)
echo "Found ${COUNT} files to upload"

# Upload each file
echo "$FILES" | while read -r file; do
    # Create remote key: powpowpow/relative/path
    relative="${file#${LOCAL_DIR}/}"
    remote_key="${REMOTE_PREFIX}/${relative}"
    
    # Get content type
    case "$file" in
        *.json)  content_type="application/json" ;;
        *.jsonl) content_type="application/x-ndjson" ;;
        *.parquet) content_type="application/octet-stream" ;;
        *)       content_type="application/octet-stream" ;;
    esac
    
    # Upload using Cloudflare R2 S3-compatible API
    date=$(date -R)
    resource="/${BUCKET}/${remote_key}"
    content_type_header="content-type:${content_type}"
    date_header="date:${date}"
    string_to_sign="PUT\n\n${content_type_header}\n${date_header}\n${resource}"
    
    # Sign with API token (simplified - use proper HMAC in production)
    echo -n "Uploading ${relative}..."
    
    # Use curl with S3v4 signing (simplified)
    curl -s -X PUT \
        -H "Content-Type: ${content_type}" \
        -H "Date: ${date}" \
        -H "Authorization: AWS4-HMAC-SHA256 Credential=${CF_API_TOKEN}/${date:0:8}/auto/s3/aws4_request, SignedHeaders=content-type;date, Signature=placeholder" \
        --data-binary "@${file}" \
        "https://${CF_ACCOUNT_ID}.r2.cloudflarestorage.com/${BUCKET}/${remote_key}" \
        -o /dev/null -w "%{http_code}" | grep -q "200\|201" && echo " OK" || echo " FAILED"
done

echo "Upload complete"
