Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
Ticket: SCRUM-14

# KM Simulator - Quick Guide

Mock QKD Key Manager for QuMail: 100 keys x 1 KB, served over a small Flask REST API.

## Run
```
pip install flask
python km_simulator.py
```
Server runs at http://127.0.0.1:8000 (open /keys/status in a browser to check).

## Key bank
`keybank.csv` holds the 100 keys (id, size, status, timestamps, base64 key material). Status changes are saved to it, so state survives restarts. Delete it to regenerate a fresh bank. Do not share it: it contains key material.

## Key states
AVAILABLE -> RESERVED (issued via `/keys/request`) -> CONSUMED (never reusable)

## Endpoints
| Method | Path            | Purpose                                                                         |
|---|-----------------|---------------------------------------------------------------------------------|
| GET | /keys/status    | Counts: total / available / reserved / consumed                                 |
| GET | /keys/available | List available key IDs                                                          |
| POST | /keys/request   | Reserve keys for `key_bytes`; returns IDs + base64 material (409 if not enough) |
| POST | /keys/consume   | Mark `key_ids` consumed (404 unknown, 409 already consumed)                     |
| GET | /keys/{key_id}  | Key metadata + material (410 if consumed)                                       |
| GET | /keys/all_keys  | Returns all keys into json format                                               |

## Quick test (curl)
```
curl http://127.0.0.1:8000/keys/status
curl -X POST http://127.0.0.1:8000/keys/request -H "Content-Type: application/json" -d "{\"key_bytes\": 2500}"
curl -X POST http://127.0.0.1:8000/keys/consume -H "Content-Type: application/json" -d "{\"key_ids\": [\"QK0001\",\"QK0002\",\"QK0003\"]}"
```
(2500 bytes reserves 3 keys, since requests round up to whole 1 KB keys.)

## Source
- From project documents: 100 x 1 KB key bank, key states, endpoint list, QK#### key IDs.
- My assumptions: CSV storage (`keybank.csv`, rewritten on every change), round-up to whole keys, material returned by `GET /keys/{key_id}`.
