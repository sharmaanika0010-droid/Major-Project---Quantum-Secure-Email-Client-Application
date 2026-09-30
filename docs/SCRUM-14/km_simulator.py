"""
SCRUM-14: QKD Key Manager (KM) simulator - stub REST API (FastAPI).

Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
Ticket: SCRUM-14

Install : pip install fastapi uvicorn
Run     : uvicorn km_simulator:app --port 8000
Docs    : http://127.0.0.1:8000/docs

Key bank: 100 keys x 1 KB (1024 bytes), generated with `secrets`.
States  : AVAILABLE -> RESERVED (issued to QuMail) -> CONSUMED (never reusable).
Storage : in-memory (stub); resets on restart.
"""
import base64
import math
import secrets
import threading
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

KEY_COUNT = 100
KEY_SIZE = 1024  # bytes (1 KB)

app = FastAPI(title="QuMail KM Simulator", version="0.1")
_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


# key_id -> record
BANK = {
    f"QK{i:04d}": {
        "key_id": f"QK{i:04d}",
        "size": KEY_SIZE,
        "status": "AVAILABLE",
        "created_at": _now(),
        "consumed_at": None,
        "_material": secrets.token_bytes(KEY_SIZE),
    }
    for i in range(1, KEY_COUNT + 1)
}


def _public(rec):
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def _count(status):
    return sum(1 for r in BANK.values() if r["status"] == status)


class KeyRequest(BaseModel):
    key_bytes: int = Field(..., gt=0, description="Bytes of key material needed")
    peer_id: str = "receiver"


class ConsumeRequest(BaseModel):
    key_ids: List[str]


@app.get("/keys/status")
def status():
    return {
        "total": len(BANK),
        "key_size_bytes": KEY_SIZE,
        "available": _count("AVAILABLE"),
        "reserved": _count("RESERVED"),
        "consumed": _count("CONSUMED"),
    }


@app.get("/keys/available")
def available():
    ids = [k for k, r in BANK.items() if r["status"] == "AVAILABLE"]
    return {"count": len(ids), "key_ids": ids}


@app.post("/keys/request")
def request_keys(req: KeyRequest):
    """Reserve enough whole keys to cover key_bytes; return IDs + material."""
    need = math.ceil(req.key_bytes / KEY_SIZE)
    with _lock:
        free = [r for r in BANK.values() if r["status"] == "AVAILABLE"]
        if len(free) < need:
            raise HTTPException(409, f"Insufficient key material: need {need} keys, {len(free)} available")
        chosen = free[:need]
        for r in chosen:
            r["status"] = "RESERVED"
        material = b"".join(r["_material"] for r in chosen)
    return {
        "peer_id": req.peer_id,
        "key_ids": [r["key_id"] for r in chosen],
        "key_length": len(material),
        "key_material": base64.b64encode(material).decode(),
    }


@app.post("/keys/consume")
def consume(req: ConsumeRequest):
    with _lock:
        for kid in req.key_ids:
            if kid not in BANK:
                raise HTTPException(404, f"Unknown key id {kid}")
            if BANK[kid]["status"] == "CONSUMED":
                raise HTTPException(409, f"Key {kid} already consumed")
        for kid in req.key_ids:
            BANK[kid]["status"] = "CONSUMED"
            BANK[kid]["consumed_at"] = _now()
    return {"consumed": req.key_ids}


@app.get("/keys/{key_id}")
def get_key(key_id: str):
    """Metadata + material (receiver side). Consumed keys are refused."""
    rec = BANK.get(key_id)
    if not rec:
        raise HTTPException(404, "Unknown key id")
    if rec["status"] == "CONSUMED":
        raise HTTPException(410, "Key already consumed")
    return {**_public(rec), "key_material": base64.b64encode(rec["_material"]).decode()}
