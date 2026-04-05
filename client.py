"""
api/client.py — Streamlit ↔ Flask API client
Falls back to direct DB/backend calls if Flask not running.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import requests as _req
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

API_BASE = "http://127.0.0.1:5050/api"
_flask_up = None  # cached status

def _is_flask_up() -> bool:
    global _flask_up
    if _flask_up is not None:
        return _flask_up
    if not REQUESTS_OK:
        _flask_up = False
        return False
    try:
        r = _req.get(f"{API_BASE}/health", timeout=1)
        _flask_up = r.status_code == 200
    except Exception:
        _flask_up = False
    return _flask_up

def _get(path, params=None):
    if _is_flask_up():
        try:
            r = _req.get(f"{API_BASE}{path}", params=params, timeout=3)
            return r.json()
        except Exception:
            pass
    return None

def _post(path, data):
    if _is_flask_up():
        try:
            r = _req.post(f"{API_BASE}{path}", json=data, timeout=3)
            return r.json()
        except Exception:
            pass
    return None

# ── Public API helpers (used by Streamlit pages) ───────────────────────────────
def api_status() -> dict:
    """Returns Flask API status."""
    up = _is_flask_up()
    return {"online": up, "url": API_BASE if up else "N/A (using local DB)"}

def get_alerts(limit=50, level=None, resolved=None):
    from database.db import get_alerts as db_get
    result = _get("/alerts", {"limit": limit, "level": level, "resolved": resolved})
    if result:
        return result.get("alerts", [])
    return db_get(limit=limit, level=level, resolved=resolved)

def create_alert(level, atype, sector, message, lat=None, lon=None, score=0.5, source="ui"):
    from database.db import insert_alert
    result = _post("/alerts", {"level":level,"type":atype,"sector":sector,
                               "message":message,"lat":lat,"lon":lon,"score":score,"source":source})
    if result:
        return result.get("alert_id")
    return insert_alert(level, atype, sector, message, lat, lon, score, source)

def resolve_alert(alert_id, resolved_by="officer"):
    from database.db import resolve_alert as db_res
    result = _post(f"/alerts/{alert_id}/resolve", {"resolved_by": resolved_by})
    if result:
        return result.get("success")
    db_res(alert_id, resolved_by)
    return True

def get_alert_stats():
    from database.db import get_alert_stats as db_stats
    result = _get("/alerts/stats")
    return result if result else db_stats()

def get_locations():
    from database.db import get_latest_locations
    result = _get("/locations")
    if result:
        return result.get("locations", [])
    return get_latest_locations()

def post_location(unit_id, unit_type, lat, lon, sector="", speed=0, heading=0):
    from database.db import upsert_location
    result = _post("/locations", {"unit_id":unit_id,"unit_type":unit_type,
                                  "lat":lat,"lon":lon,"sector":sector,
                                  "speed":speed,"heading":heading})
    if not result:
        upsert_location(unit_id, unit_type, lat, lon, sector, speed, heading)

def send_sms(to, message, alert_id=0):
    from database.db import log_notification
    result = _post("/notify/sms", {"to":to,"message":message,"alert_id":alert_id})
    if not result:
        log_notification(alert_id, "sms", to, "simulated_local")
    return result or {"success": True, "simulated": True}

def send_email(to, subject, body, alert_id=0):
    from database.db import log_notification
    result = _post("/notify/email", {"to":to,"subject":subject,"body":body,"alert_id":alert_id})
    if not result:
        log_notification(alert_id, "email", to, "simulated_local")
    return result or {"success": True, "simulated": True}

def ai_threat_analysis():
    result = _get("/ai/threat-analyze")
    if result:
        return result
    import backend as B
    rows, metrics = B.run_anomaly_detection(B.generate_sensor_readings(100))
    zones = B.predict_risk_zones()
    alerts = B.generate_alerts(10)
    threats = [a for a in alerts if a["level"] in ("CRITICAL","HIGH")]
    return {
        "anomaly_rate": round(sum(1 for r in rows if r["predicted_anomaly"])/len(rows),4),
        "model_auc": metrics["auc_roc"],
        "top_risk_sector": zones[0]["sector"] if zones else "N/A",
        "top_risk_score": zones[0]["risk_score"] if zones else 0,
        "active_threats": len(threats),
        "threat_summary": [{"level":a["level"],"message":a["message"]} for a in threats[:3]],
    }

def get_report_summary():
    result = _get("/reports/summary")
    if result:
        return result
    from database.db import get_alert_stats, get_alerts_by_type, get_alerts_by_sector, get_daily_alert_counts
    return {
        "stats": get_alert_stats(),
        "by_type": get_alerts_by_type(),
        "by_sector": get_alerts_by_sector(),
        "daily": get_daily_alert_counts(14),
    }
