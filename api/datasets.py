"""Dataset registry API. Custom snapshots are process-local and ephemeral on Vercel."""
import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

DATASETS = {
    "mpesa-checkout-batch": {
        "id": "mpesa-checkout-batch", "name": "M-Pesa checkout latency",
        "description": "Checkout amount, latency, and payment channel telemetry",
        "baseline": [
            {"amount_kes": 850, "latency_ms": 420, "channel": "STK_PUSH", "merchant": "retail", "receipt": "RCP-1001"},
            {"amount_kes": 1200, "latency_ms": 390, "channel": "STK_PUSH", "merchant": "retail", "receipt": "RCP-1002"},
            {"amount_kes": 560, "latency_ms": 460, "channel": "WEB", "merchant": "fuel", "receipt": "RCP-1003"},
            {"amount_kes": 2400, "latency_ms": 510, "channel": "STK_PUSH", "merchant": "retail", "receipt": "RCP-1004"},
            {"amount_kes": 700, "latency_ms": 405, "channel": "WEB", "merchant": "food", "receipt": "RCP-1005"},
            {"amount_kes": 1500, "latency_ms": 435, "channel": "STK_PUSH", "merchant": "fuel", "receipt": "RCP-1006"}
        ],
        "candidate": [
            {"amount_kes": 900, "latency_ms": 445, "channel": "STK_PUSH", "merchant": "retail", "receipt": "RCP-2001"},
            {"amount_kes": 1150, "latency_ms": 470, "channel": "STK_PUSH", "merchant": "retail", "receipt": "RCP-2002"},
            {"amount_kes": 610, "latency_ms": 490, "channel": "WEB", "merchant": "fuel", "receipt": "RCP-2003"},
            {"amount_kes": 2550, "latency_ms": 530, "channel": "STK_PUSH", "merchant": "retail", "receipt": "RCP-2004"},
            {"amount_kes": 730, "latency_ms": 455, "channel": "WEB", "merchant": "food", "receipt": "RCP-2005"},
            {"amount_kes": 1600, "latency_ms": 480, "channel": "STK_PUSH", "merchant": "fuel", "receipt": "RCP-2006"}
        ],
        "fieldRules": {"amount_kes": {"min": 0}, "latency_ms": {"min": 0, "max": 3000}},
        "lastDriftScore": 12
    },
    "sensor-grid-telemetry": {
        "id": "sensor-grid-telemetry", "name": "Sensor grid telemetry",
        "description": "Environmental sensor readings and device health",
        "baseline": [
            {"temperature_c": 22.1, "humidity_pct": 48, "zone": "north", "battery_pct": 91},
            {"temperature_c": 22.4, "humidity_pct": 49, "zone": "south", "battery_pct": 88},
            {"temperature_c": 21.9, "humidity_pct": 51, "zone": "north", "battery_pct": 94},
            {"temperature_c": 22.2, "humidity_pct": 47, "zone": "east", "battery_pct": 86},
            {"temperature_c": 22.5, "humidity_pct": 50, "zone": "south", "battery_pct": 90},
            {"temperature_c": 22.0, "humidity_pct": 48, "zone": "east", "battery_pct": 92}
        ],
        "candidate": [
            {"temperature_c": 22.3, "humidity_pct": 49, "zone": "north", "battery_pct": 90},
            {"temperature_c": 22.6, "humidity_pct": 50, "zone": "south", "battery_pct": 87},
            {"temperature_c": 22.0, "humidity_pct": 52, "zone": "north", "battery_pct": 93},
            {"temperature_c": 22.4, "humidity_pct": 48, "zone": "east", "battery_pct": 85},
            {"temperature_c": 22.7, "humidity_pct": 51, "zone": "south", "battery_pct": 89},
            {"temperature_c": 22.2, "humidity_pct": 49, "zone": "east", "battery_pct": 91}
        ],
        "fieldRules": {"temperature_c": {"min": -20, "max": 80}, "humidity_pct": {"min": 0, "max": 100}, "battery_pct": {"min": 0, "max": 100}},
        "lastDriftScore": 8
    },
    "user-signup-events": {
        "id": "user-signup-events", "name": "User signup events",
        "description": "Signup funnel source, plan, and profile completeness",
        "baseline": [
            {"source": "organic", "plan": "free", "age_days": 2, "email_verified": True},
            {"source": "referral", "plan": "free", "age_days": 4, "email_verified": True},
            {"source": "campaign", "plan": "pro", "age_days": 1, "email_verified": False},
            {"source": "organic", "plan": "free", "age_days": 3, "email_verified": True},
            {"source": "referral", "plan": "team", "age_days": 5, "email_verified": True},
            {"source": "organic", "plan": "pro", "age_days": 2, "email_verified": None}
        ],
        "candidate": [
            {"source": "organic", "plan": "free", "age_days": 2, "email_verified": True},
            {"source": "partner_api", "plan": "free", "age_days": 4, "email_verified": None},
            {"source": "campaign", "plan": "pro", "age_days": 1, "email_verified": False},
            {"source": "organic", "plan": "enterprise", "age_days": 3, "email_verified": True},
            {"source": "referral", "plan": "team", "age_days": 5, "email_verified": True},
            {"source": "organic", "plan": "pro", "age_days": None, "email_verified": None}
        ],
        "fieldRules": {"age_days": {"min": 0, "max": 365}},
        "lastDriftScore": 31
    }
}

def response(handler, status, payload):
    body = json.dumps(payload, allow_nan=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        response(self, 204, {})

    def do_GET(self):
        response(self, 200, {"datasets": list(DATASETS.values()), "count": len(DATASETS)})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000:
                return response(self, 413, {"error": "Payload exceeds 2 MB"})
            data = json.loads(self.rfile.read(length) or b"{}")
            name = str(data.get("name") or "Custom snapshot").strip()[:100]
            baseline, candidate = data.get("baseline"), data.get("candidate")
            if not isinstance(baseline, list) or not isinstance(candidate, list) or not baseline or not candidate:
                return response(self, 400, {"error": "baseline and candidate must be non-empty arrays"})
            if len(baseline) > 10000 or len(candidate) > 10000:
                return response(self, 400, {"error": "Each batch is limited to 10,000 records"})
            if not all(isinstance(x, dict) for x in baseline + candidate):
                return response(self, 400, {"error": "Every record must be a JSON object"})
            dataset_id = "custom-" + uuid.uuid4().hex[:10]
            item = {"id": dataset_id, "name": name, "description": "User-saved snapshot",
                    "baseline": baseline, "candidate": candidate, "fieldRules": {},
                    "lastDriftScore": None, "savedAt": datetime.now(timezone.utc).isoformat()}
            DATASETS[dataset_id] = item
            response(self, 201, {"dataset": item})
        except (ValueError, TypeError) as exc:
            response(self, 400, {"error": "Invalid JSON payload", "detail": str(exc)})

    def log_message(self, fmt, *args):
        return
