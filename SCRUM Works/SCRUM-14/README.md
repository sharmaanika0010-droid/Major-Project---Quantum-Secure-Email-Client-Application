# **Guide to SCRUM-14**

Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com

Ticket: SCRUM-14

# KM Simulator - Quick Guide

Mock QKD Key Manager for QuMail: 100 keys x 1 KB, served over a small FastAPI REST API.

## Run

```
pip install fastapi uvicorn
uvicorn km\_simulator:app --port 8000
```

Interactive docs: http://127.0.0.1:8000/docs

## Key states

AVAILABLE -> RESERVED (issued via `/keys/request`) -> CONSUMED (never reusable)

## Endpoints

| Method | Path            | Purpose                                                                          |
|--------|-----------------|----------------------------------------------------------------------------------|
| GET    | /keys/status    | Counts: total / available / reserved / consumed                                  |
| GET    | /keys/available | List available key IDs                                                           |
| POST   | /keys/request   | Reserve keys for `key\_bytes`; returns IDs + base64 material (409 if not enough) |
| POST   | /keys/consume   | Mark `key\_ids` consumed (404 unknown, 409 already consumed)                     |
| GET    | /keys/{key\_id} | Key metadata + material (410 if consumed)                                        |

## Quick test (curl)

```
curl http://127.0.0.1:8000/keys/status
curl -X POST http://127.0.0.1:8000/keys/request -H "Content-Type: application/json" -d "{\\"key\_bytes\\": 2500}"
curl -X POST http://127.0.0.1:8000/keys/consume -H "Content-Type: application/json" -d "{\\"key\_ids\\": \[\\"QK0001\\",\\"QK0002\\",\\"QK0003\\"]}"
```

(2500 bytes reserves 3 keys, since requests round up to whole 1 KB keys.)

## Source

* From project documents: 100 x 1 KB key bank, key states, endpoint list, QK#### key IDs.
* My assumptions: in-memory storage (resets on restart), round-up to whole keys, material returned by
  `GET /keys/{key\_id}`.

