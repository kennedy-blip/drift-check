"""Statistical and schema drift analysis endpoint."""
import json
import math
import statistics
from http.server import BaseHTTPRequestHandler

def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def _rate(values, predicate):
    return (sum(1 for v in values if predicate(v)) / len(values) * 100) if values else 0.0

def _safe(value):
    return round(float(value), 4) if math.isfinite(float(value)) else 0.0

def analyze_field(key, before, after, threshold, null_limit):
    b_null = _rate(before, lambda x: x is None)
    a_null = _rate(after, lambda x: x is None)
    non_null_b = [x for x in before if x is not None]
    non_null_a = [x for x in after if x is not None]
    numeric = bool(non_null_b or non_null_a) and all(_is_number(x) for x in non_null_b + non_null_a)
    issues, metrics = [], {}
    severity = 0.0
    if numeric:
        bm = statistics.mean(non_null_b) if non_null_b else 0.0
        am = statistics.mean(non_null_a) if non_null_a else 0.0
        bs = statistics.pstdev(non_null_b) if len(non_null_b) > 1 else 0.0
        ass = statistics.pstdev(non_null_a) if len(non_null_a) > 1 else 0.0
        scale = bs if bs > 1e-12 else max(abs(bm) * 0.01, 1.0)
        z = abs(am - bm) / scale
        std_shift = abs(ass - bs) / max(bs, 1e-9) * 100 if bs > 1e-9 else (100.0 if ass > 1e-9 else 0.0)
        metrics.update({"baselineMean": _safe(bm), "candidateMean": _safe(am),
                        "baselineStdDev": _safe(bs), "candidateStdDev": _safe(ass),
                        "zScore": _safe(z), "stdDevShiftPct": _safe(std_shift),
                        "baselineMin": min(non_null_b) if non_null_b else None,
                        "baselineMax": max(non_null_b) if non_null_b else None,
                        "candidateMin": min(non_null_a) if non_null_a else None,
                        "candidateMax": max(non_null_a) if non_null_a else None})
        if z >= threshold:
            issues.append("Mean shift exceeds Z-score threshold")
            severity += min(45, 15 + z * 5)
        if std_shift >= 50:
            issues.append("Population standard deviation changed materially")
            severity += min(20, std_shift / 5)
        rules = {}
        if non_null_b:
            rules = {"min": min(non_null_b), "max": max(non_null_b)}
        for value in non_null_a:
            if (rules and (value < rules["min"] or value > rules["max"])):
                issues.append("Candidate value outside baseline observed range")
                severity += 15
                break
    else:
        b_counts, a_counts = {}, {}
        for value in non_null_b: b_counts[str(value)] = b_counts.get(str(value), 0) + 1
        for value in non_null_a: a_counts[str(value)] = a_counts.get(str(value), 0) + 1
        unseen = sorted(set(a_counts) - set(b_counts))
        metrics.update({"baselineUnique": len(b_counts), "candidateUnique": len(a_counts),
                        "unseenValues": unseen[:20],
                        "baselineTopValues": sorted(b_counts.items(), key=lambda x: -x[1])[:5],
                        "candidateTopValues": sorted(a_counts.items(), key=lambda x: -x[1])[:5]})
        if unseen:
            issues.append("Unseen categorical values detected")
            severity += min(35, 15 + len(unseen) * 5)
        # Compare categorical proportions using total variation distance.
        total_b, total_a = max(len(non_null_b), 1), max(len(non_null_a), 1)
        keys = set(b_counts) | set(a_counts)
        tvd = 0.5 * sum(abs(b_counts.get(k, 0) / total_b - a_counts.get(k, 0) / total_a) for k in keys)
        metrics["distributionShiftPct"] = _safe(tvd * 100)
        if tvd >= 0.25:
            issues.append("Categorical distribution shifted")
            severity += min(25, tvd * 40)
    null_delta = a_null - b_null
    metrics.update({"baselineNullPct": _safe(b_null), "candidateNullPct": _safe(a_null),
                    "nullDeltaPct": _safe(null_delta), "type": "numeric" if numeric else "categorical"})
    if null_delta > null_limit:
        issues.append("Null rate increased beyond configured limit")
        severity += min(40, 15 + (null_delta - null_limit))
    if not non_null_a:
        issues.append("Candidate field contains no non-null values")
        severity += 35
    severity = min(100.0, severity)
    status = "DRIFT_DETECTED" if severity >= 55 else ("WARNING" if severity > 0 else "HEALTHY")
    return {"field": key, "status": status, "severity": _safe(severity), "issues": list(dict.fromkeys(issues)), **metrics}

def run_analysis(data):
    baseline, candidate = data.get("baselineRecords"), data.get("candidateRecords")
    if not isinstance(baseline, list) or not isinstance(candidate, list) or not baseline or not candidate:
        raise ValueError("baselineRecords and candidateRecords must be non-empty arrays")
    if len(baseline) > 10000 or len(candidate) > 10000:
        raise ValueError("Each batch is limited to 10,000 records")
    if not all(isinstance(r, dict) for r in baseline + candidate):
        raise ValueError("Every record must be a JSON object")
    threshold = float(data.get("zScoreThreshold", 2.5))
    null_limit = float(data.get("maxNullDeltaPct", 10))
    if not math.isfinite(threshold) or threshold <= 0 or threshold > 20:
        raise ValueError("zScoreThreshold must be greater than 0 and at most 20")
    if not math.isfinite(null_limit) or null_limit < 0 or null_limit > 100:
        raise ValueError("maxNullDeltaPct must be between 0 and 100")
    keys = sorted(set().union(*(r.keys() for r in baseline), *(r.keys() for r in candidate)))
    fields = []
    for key in keys:
        b = [r.get(key) for r in baseline]
        a = [r.get(key) for r in candidate]
        result = analyze_field(str(key), b, a, threshold, null_limit)
        if any(key not in r for r in baseline) or any(key not in r for r in candidate):
            result["issues"].append("Field missing from one or more records")
            result["severity"] = min(100, result["severity"] + 20)
            result["status"] = "DRIFT_DETECTED" if result["severity"] >= 55 else "WARNING"
        fields.append(result)
    score = round(sum(f["severity"] for f in fields) / max(len(fields), 1))
    status = "DRIFT_DETECTED" if score >= 55 or any(f["status"] == "DRIFT_DETECTED" for f in fields) else ("WARNING" if score > 0 else "HEALTHY")
    return {"datasetId": data.get("datasetId"), "status": status, "driftScore": score,
            "summary": {"baselineRecords": len(baseline), "candidateRecords": len(candidate),
                        "fieldsChecked": len(fields), "fieldsWithDrift": sum(1 for f in fields if f["status"] != "HEALTHY")},
            "thresholds": {"zScoreThreshold": threshold, "maxNullDeltaPct": null_limit},
            "fields": fields}

def send(handler, status, payload):
    body = json.dumps(payload, allow_nan=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send(self, 204, {})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000:
                return send(self, 413, {"error": "Payload exceeds 2 MB"})
            data = json.loads(self.rfile.read(length) or b"{}")
            send(self, 200, run_analysis(data))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            send(self, 400, {"error": str(exc)})
        except Exception:
            send(self, 500, {"error": "Analysis failed unexpectedly"})

    def log_message(self, fmt, *args):
        return
