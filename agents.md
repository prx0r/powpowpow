# Agents Reference

## Cloudflare Account Access (Email Routing / Email Workers)

### Credentials Location
- `/home/box/cloudflare` — older token (expired)
- `/home/box/Documents/safe/cloudflare3` — **WORKING token**

### Account Details
- **Account ID:** `954612afb5a97bb15dddcdc70176813d`
- **API Token (working):** `REDACTED` — stored in `/home/box/Documents/safe/cloudflare3`
- **R2 Access Key ID:** `REDACTED` — same file
- **R2 Secret Access Key:** `REDACTED` — same file
- **R2 S3 Endpoint:** `https://954612afb5a97bb15dddcdc70176813d.r2.cloudflarestorage.com`

### Verify API Token
```bash
TOKEN=$(cat /home/box/Documents/safe/cloudflare3)
ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"
curl -X GET "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/tokens/verify" \
     -H "Authorization: Bearer $TOKEN"
```

### Query Email Inbox (D1)
```bash
TOKEN=$(cat /home/box/Documents/safe/cloudflare3)
ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"
DB_ID="1a2b7b3e-cfad-4455-ad5f-133903e4265b"
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/d1/database/$DB_ID/query" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"sql": "SELECT message_id, subject, sender, received_at, classification FROM messages ORDER BY received_at DESC LIMIT 50"}'
```

### Download Raw Emails from R2
```python
import boto3, os

# Read credentials from file
with open(os.path.expanduser('~/Documents/safe/cloudflare3')) as f:
    token = f.read().strip()

s3 = boto3.client('s3',
    endpoint_url='https://954612afb5a97bb15dddcdc70176813d.r2.cloudflarestorage.com',
    aws_access_key_id='REDACTED',  # read from cloudflare3 env or secrets manager
    aws_secret_access_key='REDACTED',
    region_name='auto'
)
# List objects
for page in s3.get_paginator('list_objects_v2').paginate(
    Bucket='cmail-raw', Prefix='email/raw/intelligentothers.xyz/agents/'
):
    for obj in page.get('Contents', []):
        s3.download_file('cmail-raw', obj['Key'], f"emails/{obj['Key'].split('/')[-1]}")
```

### List Workers
```bash
TOKEN=$(cat /home/box/Documents/safe/cloudflare3)
ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"
curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/workers/scripts" \
     -H "Authorization: Bearer $TOKEN"
```

### List R2 Buckets
```bash
TOKEN=$(cat /home/box/Documents/safe/cloudflare3)
ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"
curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/r2/buckets" \
     -H "Authorization: Bearer $TOKEN"
```

### D1 Databases
| Name | UUID |
|------|------|
| cmail-index | `1a2b7b3e-cfad-4455-ad5f-133903e4265b` |
| freak-town | `a2221653-a6d6-4c13-aedc-9f64fa3cee93` |
| cancelme | `96e091f0-2478-46cd-9a17-bd884838a78c` |
| platinum-factory-db | `dd8eb40f-9eb0-41c0-9324-99c5d9c118f9` |
| factory-db | `9bc3df37-63f5-474a-881f-7f5dfe1fad9e` |
| atlas-db | `bd6337b3-09d4-4b5b-ad1c-fe62e480386b` |

### Email System (cmail)
- **Worker:** `cmail` at `cmail.tradesprior.workers.dev`
- **D1:** `cmail-index` — messages, mailboxes, domains, aliases
- **R2:** `cmail-raw` — raw .eml files
- **Domains:** intelligentothers.xyz, agentcom.org, drawdle.dev, feedify.dev, breadup.dev
- **Mailboxes:** agents@, hello@, support@, billing@ per domain
- **Total messages:** 366 as of 2026-09-20
- **Local copy:** `/home/box/powpowpow/emails/` (88 most recent .eml downloaded + index)

### Notes
- R2 requires SigV4 signing — use `boto3` with the endpoint URL
- To rotate token: Cloudflare Dashboard → My Profile → API Tokens → Create Token
- cmail worker source: `/home/box/influence/cmail/`
