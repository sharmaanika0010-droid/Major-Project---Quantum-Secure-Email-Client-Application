Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
Ticket: SCRUM-20

# [Day 4] KM API: /get_key endpoint

Task: `/get_key` returns an unused key and marks it consumed.

## What changed
`km_simulator.py` is the SCRUM-14 file with one new endpoint added (nothing else touched). It uses the existing Flask app, `KEY_BANK`, lock, `save()` and `keybank.csv` from SCRUM-14. `keybank.csv` is not included: the existing one is reused (it is created automatically if missing).

## Run
```
pip install flask
python km_simulator.py
```

## Endpoint
`POST /get_key` ->
```
{"key_id": "QK0001", "size": 1024, "status": "CONSUMED", "created_at": "...",
 "consumed_at": "...", "key_material": "<base64>"}
```
- Takes the first AVAILABLE key (RESERVED keys are skipped), sets it CONSUMED with `consumed_at`, and saves to `keybank.csv` inside the existing lock.
- Bank empty: HTTP 409 `{"detail": "No unused keys left in key bank"}`.
- Quick test: `curl -X POST http://127.0.0.1:5000/get_key`

## Source of data
From your project documents/uploads: the Flask simulator, 100 x 1024-byte keys, `QK0001` IDs, statuses, CSV storage, response field names and the `error()` style.
My assumptions: POST because the call changes state; 409 on exhaustion (same as `/keys/request`); response fields mirror `GET /keys/<key_id>`.
Tested (on a fresh 100-key bank): consumed keys are unique, status counts update, CSV saved, `GET /keys/<id>` returns 410 for a key taken via `/get_key`, RESERVED keys are skipped, 409 when empty.

## Commit message (when you commit)
`SCRUM-20: Add /get_key endpoint returning unused key and marking it consumed`
