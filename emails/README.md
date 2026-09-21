# agents@intelligentothers.xyz — Email Inbox

**Total raw .eml files in R2:** 344
**D1 database:** cmail-index (1a2b7b3e-cfad-4455-ad5f-133903e4265b)
**R2 bucket:** cmail-raw
**Worker:** cmail (cmail.tradesprior.workers.dev)

## How to download all

```bash
TOKEN=$(cat ~/Documents/safe/cloudflare3)
ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"
DB_ID="1a2b7b3e-cfad-4455-ad5f-133903e4265b"
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/d1/database/$DB_ID/query" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"sql": "SELECT message_id, subject, sender, received_at, r2_raw_key FROM messages ORDER BY received_at DESC"}'
```

```python
import boto3, os
with open(os.path.expanduser('~/Documents/safe/cloudflare3')) as f:
    token = f.read().strip()
s3 = boto3.client('s3',
    endpoint_url='https://954612afb5a97bb15dddcdc70176813d.r2.cloudflarestorage.com',
    aws_access_key_id='REDACTED',
    aws_secret_access_key='REDACTED',
    region_name='auto'
)
```
