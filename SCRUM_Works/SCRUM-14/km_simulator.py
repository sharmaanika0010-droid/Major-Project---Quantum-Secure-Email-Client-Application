import base64
import csv
import math
import os
import secrets
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request

KEY_COUNT = 100
KEY_SIZE = 1024
CSV_FILE = os.path.join(os.path.dirname(__file__), "keybank.csv")
FIELDS = ["key_id", "size", "status", "created_at", "consumed_at", "key_material_b64"]

app = Flask(__name__)
lock = threading.Lock()


def now():
	return datetime.now(timezone.utc).isoformat()


def error(current_status, message):
	return jsonify({"detail": message}), current_status


def save():
	"""Save the key bank to CSV. Caller must hold lock."""
	with open(CSV_FILE, "w", newline="") as f:
		writer = csv.DictWriter(f, fieldnames=FIELDS)
		writer.writeheader()
		for key in KEY_BANK.values():
			writer.writerow({
				"key_id": key["key_id"],
				"size": key["size"],
				"status": key["status"],
				"created_at": key["created_at"],
				"consumed_at": key["consumed_at"] or "",
				"key_material_b64": base64.b64encode(key["material"]).decode(),
			})


def load():
	bank = {}
	with open(CSV_FILE, newline="") as f:
		for row in csv.DictReader(f):
			bank[row["key_id"]] = {
				"key_id": row["key_id"],
				"size": int(row["size"]),
				"status": row["status"],
				"created_at": row["created_at"],
				"consumed_at": row["consumed_at"] or None,
				"material": base64.b64decode(row["key_material_b64"]),
			}
	return bank


def create_bank():
	return {
		f"QK{i:04d}": {
			"key_id": f"QK{i:04d}",
			"size": KEY_SIZE,
			"status": "AVAILABLE",
			"created_at": now(),
			"consumed_at": None,
			"material": secrets.token_bytes(KEY_SIZE),
		}
		for i in range(1, KEY_COUNT + 1)
	}


KEY_BANK = load() if os.path.exists(CSV_FILE) else create_bank()

if not os.path.exists(CSV_FILE):
	save()


@app.get("/keys/status")
def status():
	counts = {
		status: sum(key["status"] == status for key in KEY_BANK.values())
		for status in ("AVAILABLE", "RESERVED", "CONSUMED")
	}
	
	return jsonify({
		"total": len(KEY_BANK),
		"key_size_bytes": KEY_SIZE,
		"available": counts["AVAILABLE"],
		"reserved": counts["RESERVED"],
		"consumed": counts["CONSUMED"],
	})


@app.get("/keys/available")
def available():
	ids = [
		key_id
		for key_id, key in KEY_BANK.items()
		if key["status"] == "AVAILABLE"
	]
	
	return jsonify({
		"count": len(ids),
		"key_ids": ids,
	})


@app.post("/keys/request")
def request_keys():
	body = request.get_json(silent=True) or {}
	key_bytes = body.get("key_bytes")
	
	if not isinstance(key_bytes, int) or isinstance(key_bytes, bool) or key_bytes <= 0:
		return error(422, "key_bytes must be a positive integer")
	
	need = math.ceil(key_bytes / KEY_SIZE)
	
	with lock:
		available_keys = [
			key for key in KEY_BANK.values()
			if key["status"] == "AVAILABLE"
		]
		
		if len(available_keys) < need:
			return error(
				409,
				f"Insufficient key material: need {need} keys, "
				f"{len(available_keys)} available",
			)
		
		chosen = available_keys[:need]
		
		for key in chosen:
			key["status"] = "RESERVED"
		
		save()
	
	material = b"".join(key["material"] for key in chosen)
	
	return jsonify({
		"peer_id": body.get("peer_id", "receiver"),
		"key_ids": [key["key_id"] for key in chosen],
		"key_length": len(material),
		"key_material": base64.b64encode(material).decode(),
	})


@app.post("/keys/consume")
def consume():
	body = request.get_json(silent=True) or {}
	key_ids = body.get("key_ids")
	
	if not isinstance(key_ids, list) or not key_ids:
		return error(422, "key_ids must be a non-empty list")
	
	with lock:
		for key_id in key_ids:
			if key_id not in KEY_BANK:
				return error(404, f"Unknown key id {key_id}")
			
			if KEY_BANK[key_id]["status"] == "CONSUMED":
				return error(409, f"Key {key_id} already consumed")
		
		for key_id in key_ids:
			KEY_BANK[key_id]["status"] = "CONSUMED"
			KEY_BANK[key_id]["consumed_at"] = now()
		
		save()
	
	return jsonify({"consumed": key_ids})


@app.get("/keys/<key_id>")
def get_key(key_id):
	key = KEY_BANK.get(key_id)
	
	if not key:
		return error(404, "Unknown key id")
	
	if key["status"] == "CONSUMED":
		return error(410, "Key already consumed")
	
	return jsonify({
		"key_id": key["key_id"],
		"size": key["size"],
		"status": key["status"],
		"created_at": key["created_at"],
		"consumed_at": key["consumed_at"],
		"key_material": base64.b64encode(key["material"]).decode(),
	})


@app.get("/keys/all_keys")
def all_keys():
	return jsonify([
		{
			"key_id": key["key_id"],
			"size": key["size"],
			"status": key["status"],
			"created_at": key["created_at"],
			"consumed_at": key["consumed_at"],
		}
		for key in KEY_BANK.values()
	])


if __name__ == "__main__":
	app.run()
