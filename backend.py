"""
backend.py — Sentinel Data & ML Engine
Simulates sensor ingestion, anomaly detection, object classification,
risk prediction, and alert prioritization without external ML deps.
"""

import random
import math
import hashlib
from datetime import datetime, timedelta

# ── Reproducible seed ──────────────────────────────────────────────────────────
random.seed(42)

SECTORS = ["A1","A2","A3","B1","B2","B3","C1","C2","C3","D1","D2","D3"]
SENSOR_TYPES = ["Thermal","Motion","Acoustic","Seismic","Visual","Radar"]
OBJECT_CLASSES = ["Human","Vehicle","Wildlife","Unknown","Aircraft"]
THREAT_LEVELS = ["CRITICAL","HIGH","MEDIUM","LOW","CLEAR"]

# ── Sensor data generation ─────────────────────────────────────────────────────
def generate_sensor_readings(n=500, seed=None):
    if seed: random.seed(seed)
    rows = []
    now = datetime.now()
    for i in range(n):
        ts = now - timedelta(minutes=random.randint(0, 1440))
        sector = random.choice(SECTORS)
        stype  = random.choice(SENSOR_TYPES)
        normal = random.gauss(0.3, 0.15)
        # Inject anomalies ~8% of records
        is_anomaly = random.random() < 0.08
        value = random.uniform(0.75, 1.0) if is_anomaly else max(0, min(1, normal))
        rows.append({
            "timestamp":   ts.strftime("%Y-%m-%d %H:%M"),
            "sector":      sector,
            "sensor_type": stype,
            "value":       round(value, 4),
            "anomaly":     is_anomaly,
            "confidence":  round(random.uniform(0.82, 0.99) if is_anomaly else random.uniform(0.5, 0.78), 3),
            "lat":         round(random.uniform(28.0, 32.0), 5),
            "lon":         round(random.uniform(72.0, 77.0), 5),
        })
    return rows


def get_sensor_stats(rows):
    total      = len(rows)
    anomalies  = sum(1 for r in rows if r["anomaly"])
    by_sector  = {}
    by_type    = {}
    for r in rows:
        by_sector[r["sector"]] = by_sector.get(r["sector"], 0) + (1 if r["anomaly"] else 0)
        by_type[r["sensor_type"]] = by_type.get(r["sensor_type"], 0) + 1
    return {
        "total": total,
        "anomaly_count": anomalies,
        "anomaly_rate": round(anomalies / total * 100, 2),
        "by_sector": by_sector,
        "by_type": by_type,
    }


# ── Isolation Forest (pure-Python stub) ───────────────────────────────────────
def isolation_score(value: float, mean: float = 0.3, std: float = 0.15) -> float:
    """Simplified anomaly score: higher = more anomalous."""
    z = abs(value - mean) / max(std, 1e-6)
    return round(min(1.0, z / 4.0), 4)


def run_anomaly_detection(rows):
    results = []
    for r in rows:
        score = isolation_score(r["value"])
        pred  = score > 0.55
        results.append({**r, "anomaly_score": score, "predicted_anomaly": pred})
    tp = sum(1 for r in results if r["anomaly"] and r["predicted_anomaly"])
    fp = sum(1 for r in results if not r["anomaly"] and r["predicted_anomaly"])
    tn = sum(1 for r in results if not r["anomaly"] and not r["predicted_anomaly"])
    fn = sum(1 for r in results if r["anomaly"] and not r["predicted_anomaly"])
    precision = tp / max(tp + fp, 1)
    recall    = tp / max(tp + fn, 1)
    f1        = 2 * precision * recall / max(precision + recall, 1e-6)
    auc_roc   = round(0.91 + random.uniform(-0.02, 0.04), 4)
    return results, {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "auc_roc":   auc_roc,
        "accuracy":  round((tp + tn) / len(results), 4),
    }


# ── Object classifier (rule-based stub mimicking YOLO) ────────────────────────
def classify_object(sensor_value: float, sensor_type: str, time_hour: int) -> dict:
    probs = {"Human": 0.1, "Vehicle": 0.1, "Wildlife": 0.4, "Unknown": 0.2, "Aircraft": 0.05}
    if sensor_value > 0.8:
        probs = {"Human": 0.55, "Vehicle": 0.25, "Wildlife": 0.05, "Unknown": 0.1, "Aircraft": 0.05}
    elif sensor_value > 0.6:
        probs = {"Human": 0.35, "Vehicle": 0.20, "Wildlife": 0.25, "Unknown": 0.15, "Aircraft": 0.05}
    if sensor_type == "Radar":
        probs["Vehicle"] += 0.15; probs["Human"] -= 0.1
    if sensor_type == "Acoustic" and time_hour in range(22, 5):
        probs["Human"] += 0.1
    total = sum(probs.values())
    probs = {k: round(v / total, 3) for k, v in probs.items()}
    label = max(probs, key=probs.get)
    return {"label": label, "probabilities": probs, "confidence": probs[label]}


# ── Risk zone predictor ────────────────────────────────────────────────────────
_BASE_RISK = {
    "A1":0.82,"A2":0.45,"A3":0.31,"B1":0.67,"B2":0.88,"B3":0.52,
    "C1":0.24,"C2":0.61,"C3":0.73,"D1":0.19,"D2":0.44,"D3":0.56,
}

def predict_risk_zones(time_hour: int = None) -> list:
    if time_hour is None:
        time_hour = datetime.now().hour
    night_boost = 1.3 if time_hour in list(range(22, 24)) + list(range(0, 5)) else 1.0
    results = []
    for sector, base in _BASE_RISK.items():
        noise = random.uniform(-0.05, 0.05)
        risk  = min(1.0, base * night_boost + noise)
        if   risk >= 0.80: level = "CRITICAL"
        elif risk >= 0.60: level = "HIGH"
        elif risk >= 0.40: level = "MEDIUM"
        else:              level = "LOW"
        results.append({"sector": sector, "risk_score": round(risk, 3), "risk_level": level})
    return sorted(results, key=lambda x: x["risk_score"], reverse=True)


# ── Alert engine ───────────────────────────────────────────────────────────────
_ALERT_MSGS = {
    "CRITICAL": [
        "Multiple contacts — human-class objects crossing perimeter",
        "Thermal signatures — 3+ individuals in restricted zone",
        "High-confidence intrusion — Sector perimeter breach",
        "Coordinated movement pattern — possible group incursion",
    ],
    "HIGH": [
        "Vehicle stopped in restricted zone — ID required",
        "Seismic anomaly — possible underground activity",
        "Acoustic signature — unidentified motorized unit",
        "Radar track — low-altitude object approaching",
    ],
    "MEDIUM": [
        "Perimeter sensor spike — classifying",
        "Motion detected — wildlife/human ambiguous",
        "Thermal fade — sensor needs calibration",
        "Network gap — 3 sensors offline in Sector",
    ],
    "LOW": [
        "Wildlife detected — coyote class, suppressed",
        "Wind gust artifact — filtered by model",
        "Sensor drift — recalibrating baseline",
        "False trigger — rain interference",
    ],
}

def generate_alerts(n: int = 20) -> list:
    alerts = []
    now = datetime.now()
    weights = {"CRITICAL": 0.08, "HIGH": 0.18, "MEDIUM": 0.34, "LOW": 0.40}
    levels  = list(weights.keys())
    wts     = list(weights.values())
    for i in range(n):
        level   = random.choices(levels, wts)[0]
        sector  = random.choice(SECTORS)
        msg     = random.choice(_ALERT_MSGS[level])
        minutes = random.randint(0, 180)
        ts      = now - timedelta(minutes=minutes)
        score   = {"CRITICAL":0.92,"HIGH":0.74,"MEDIUM":0.51,"LOW":0.28}[level] + random.uniform(-0.05,0.05)
        suppressed = level == "LOW" and random.random() < 0.65
        alerts.append({
            "id":        f"ALT-{1000+i}",
            "level":     level,
            "sector":    sector,
            "message":   f"{msg} [{sector}]",
            "timestamp": ts.strftime("%H:%M:%S"),
            "score":     round(score, 3),
            "suppressed": suppressed,
            "responder": "AUTO-SUPPRESS" if suppressed else random.choice(["UNIT-7","UNIT-3","UNIT-9","PENDING"]),
        })
    return sorted(alerts, key=lambda x: x["score"], reverse=True)


# ── Historical incidents (for EDA) ─────────────────────────────────────────────
def generate_incidents(n: int = 200) -> list:
    types = ["Intrusion","Vehicle Crossing","UAV Sighting","Sensor Tampering","False Alarm","Wildlife"]
    outcomes = ["Intercepted","Escaped","Investigated","Auto-Cleared","Under Review"]
    rows = []
    now = datetime.now()
    for i in range(n):
        days_ago = random.randint(0, 365*3)
        ts = now - timedelta(days=days_ago)
        itype = random.choice(types)
        rows.append({
            "incident_id": f"INC-{2000+i}",
            "date":        ts.strftime("%Y-%m-%d"),
            "month":       ts.strftime("%b"),
            "year":        ts.year,
            "sector":      random.choice(SECTORS),
            "type":        itype,
            "severity":    random.choice(THREAT_LEVELS[:-1]),
            "outcome":     random.choice(outcomes),
            "duration_min": random.randint(5, 240),
            "responders":  random.randint(1, 8),
            "lat":         round(random.uniform(28.0, 32.0), 4),
            "lon":         round(random.uniform(72.0, 77.0), 4),
        })
    return rows


# ── Time-series for charts ─────────────────────────────────────────────────────
def get_hourly_activity(days: int = 7) -> list:
    """Returns hourly anomaly counts for the past N days."""
    rows = []
    now = datetime.now()
    for h in range(days * 24):
        ts = now - timedelta(hours=h)
        hour = ts.hour
        # Night hours have higher activity
        base = 4 if hour in list(range(22,24)) + list(range(0,5)) else 1.5
        count = max(0, int(random.gauss(base, 1.2)))
        rows.append({"datetime": ts.strftime("%Y-%m-%d %H:00"), "hour": hour, "anomalies": count})
    return list(reversed(rows))


def get_model_metrics_history(epochs: int = 30) -> list:
    """Simulated training curve."""
    rows = []
    loss, val_loss, acc, val_acc = 1.2, 1.4, 0.55, 0.50
    for e in range(1, epochs + 1):
        loss     = max(0.05, loss * 0.92 + random.gauss(0, 0.01))
        val_loss = max(0.08, val_loss * 0.91 + random.gauss(0, 0.015))
        acc      = min(0.985, acc + random.gauss(0.018, 0.005))
        val_acc  = min(0.974, val_acc + random.gauss(0.016, 0.006))
        rows.append({
            "epoch": e,
            "loss": round(loss, 4),
            "val_loss": round(val_loss, 4),
            "accuracy": round(acc, 4),
            "val_accuracy": round(val_acc, 4),
        })
    return rows
