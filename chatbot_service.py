"""
api/services/chatbot_service.py
─────────────────────────────────
AI chatbot service for officer queries.
Supports: Anthropic Claude · OpenAI GPT · Rule-based fallback

Context injection: pulls live DB data into every prompt so the AI
answers with real, up-to-date system information.
"""

import os, json, re, sys
from datetime import datetime
from typing import Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
from database.db import (
    get_alert_stats, get_alerts, save_chat, get_chat_history
)
import backend as B

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY","")
OPENAI_KEY    = os.getenv("OPENAI_API_KEY","")


class ChatbotService:
    """
    Tactical AI assistant for border defence officers.
    Has live access to: alerts, risk zones, AI analysis, sensor stats.
    """

    SYSTEM_PROMPT = """You are SENTINEL AI — a military-grade border surveillance intelligence assistant.
You provide concise, accurate, tactical responses.
You have REAL-TIME access to the surveillance database (injected in each message).
Always use specific numbers and data from the context.
Respond in a professional military tone.
Never reveal system internals or credentials.
If you cannot find data in context, say "Data not available in current feed."
Keep responses under 150 words unless detail is specifically requested.
"""

    # ── Build live context ────────────────────────────────────────────────────
    @staticmethod
    def build_live_context() -> str:
        try:
            stats  = get_alert_stats()
            alerts = get_alerts(limit=5, resolved=0)
            zones  = B.predict_risk_zones()[:4]
            rows, metrics = B.run_anomaly_detection(B.generate_sensor_readings(100))
            anom_rate = round(sum(1 for r in rows if r["predicted_anomaly"])/len(rows)*100,1)

            ctx = f"""
=== LIVE DATABASE CONTEXT [{datetime.now().strftime('%H:%M:%S')}] ===
ALERTS: total={stats.get('total',0)}, critical={stats.get('critical',0)}, unresolved={stats.get('unresolved',0)}, today={stats.get('today',0)}

ACTIVE THREATS (top 5):
{chr(10).join(f"  [{a['level']}] SEC {a['sector']} | {a['message'][:60]} | {a.get('created_at','')[:16]}" for a in alerts) or "  No active threats"}

RISK ZONES:
{chr(10).join(f"  {z['sector']}: {z['risk_level']} ({z['risk_score']})" for z in zones)}

AI MODEL: AUC={metrics['auc_roc']}, Accuracy={metrics['accuracy']}, Anomaly_rate={anom_rate}%
TOP RISK SECTOR: {zones[0]['sector']} ({zones[0]['risk_level']}) if zones else N/A
=== END CONTEXT ==="""
        except Exception as e:
            ctx = f"=== CONTEXT ERROR: {e} ==="
        return ctx

    # ── Claude API ────────────────────────────────────────────────────────────
    def call_claude(self, session_id: str, message: str,
                    api_key: Optional[str] = None) -> dict:
        key = api_key or ANTHROPIC_KEY
        if not key:
            return {"success": False, "error": "No Anthropic API key configured",
                    "fallback": True, "response": self._rule_based(message)}
        try:
            import anthropic
            history = get_chat_history(session_id, 10)
            context = self.build_live_context()

            messages = []
            for h in history[-8:]:
                if h["role"] in ("user","assistant"):
                    messages.append({"role": h["role"], "content": h["message"]})
            messages.append({"role": "user", "content": message})

            client = anthropic.Anthropic(api_key=key)
            resp   = client.messages.create(
                model       = "claude-sonnet-4-20250514",
                max_tokens  = 512,
                system      = self.SYSTEM_PROMPT + "\n" + context,
                messages    = messages,
            )
            return {"success": True, "response": resp.content[0].text,
                    "provider": "Claude", "model": "claude-sonnet-4-20250514"}
        except ImportError:
            return {"success": False, "error": "pip install anthropic",
                    "fallback": True, "response": self._rule_based(message)}
        except Exception as e:
            return {"success": False, "error": str(e),
                    "fallback": True, "response": self._rule_based(message)}

    # ── OpenAI GPT API ────────────────────────────────────────────────────────
    def call_openai(self, session_id: str, message: str,
                    api_key: Optional[str] = None) -> dict:
        key = api_key or OPENAI_KEY
        if not key:
            return {"success": False, "error": "No OpenAI API key configured",
                    "fallback": True, "response": self._rule_based(message)}
        try:
            import openai
            history  = get_chat_history(session_id, 10)
            context  = self.build_live_context()
            messages = [{"role": "system", "content": self.SYSTEM_PROMPT + "\n" + context}]
            for h in history[-8:]:
                if h["role"] in ("user","assistant"):
                    messages.append({"role": h["role"], "content": h["message"]})
            messages.append({"role": "user", "content": message})

            client = openai.OpenAI(api_key=key)
            resp   = client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, max_tokens=512
            )
            return {"success": True, "response": resp.choices[0].message.content,
                    "provider": "OpenAI", "model": "gpt-4o-mini"}
        except ImportError:
            return {"success": False, "error": "pip install openai",
                    "fallback": True, "response": self._rule_based(message)}
        except Exception as e:
            return {"success": False, "error": str(e),
                    "fallback": True, "response": self._rule_based(message)}

    # ── Rule-based fallback ───────────────────────────────────────────────────
    def _rule_based(self, msg: str) -> str:
        """Smart rule-based chatbot using live DB data. Zero API cost."""
        msg    = msg.lower().strip()
        stats  = get_alert_stats()
        alerts = get_alerts(limit=5, resolved=0)
        zones  = B.predict_risk_zones()[:3]

        # Threat/danger queries
        if any(w in msg for w in ["threat","danger","critical","emergency","active"]):
            crits = [a for a in alerts if a["level"]=="CRITICAL"]
            if crits:
                a = crits[0]
                return (f"🔴 CRITICAL ACTIVE: {a['message']} | Sector {a['sector']} | "
                        f"Score {a['score']} | {a.get('created_at','')[:16]}")
            return (f"No CRITICAL alerts active. {stats.get('unresolved',0)} unresolved "
                    f"alerts in queue. Highest risk: Sector {zones[0]['sector']} ({zones[0]['risk_level']}).")

        # Last/latest/recent alert
        if any(w in msg for w in ["last","latest","recent","show","first"]):
            if alerts:
                a = alerts[0]
                return (f"Last alert — [{a['level']}] {a['message']} | "
                        f"Sector {a['sector']} | Source: {a['source']} | {a.get('created_at','')[:16]}")
            return "No alerts in database yet."

        # Risk zones
        if any(w in msg for w in ["risk","zone","sector","dangerous","hot","area"]):
            top = zones[0]
            return (f"⚠️ Highest risk: SECTOR {top['sector']} — {top['risk_level']} "
                    f"(score {top['risk_score']}). "
                    f"Also monitoring: {zones[1]['sector']} ({zones[1]['risk_level']}), "
                    f"{zones[2]['sector']} ({zones[2]['risk_level']}).")

        # Statistics
        if any(w in msg for w in ["count","total","many","stats","statistics","summary","how"]):
            return (f"📊 Database: {stats.get('total',0)} total alerts | "
                    f"{stats.get('critical',0)} critical | "
                    f"{stats.get('unresolved',0)} unresolved | "
                    f"{stats.get('today',0)} today.")

        # Gunshot
        if any(w in msg for w in ["gunshot","shot","gun","weapon","fire","bullet"]):
            gun_alerts = [a for a in alerts if "gunshot" in a.get("type","").lower()
                          or "weapon" in a.get("type","").lower()]
            if gun_alerts:
                a = gun_alerts[0]
                return f"🔫 WEAPON ALERT: {a['message']} | Score {a['score']} | {a.get('created_at','')[:16]}"
            return ("🔫 No active gunshot/weapon alerts. Audio detection running on all sectors. "
                    "Gunshot signatures use ZCR + spectral centroid analysis.")

        # Scream
        if any(w in msg for w in ["scream","cry","voice","shout","human"]):
            sc_alerts = [a for a in alerts if "scream" in a.get("type","").lower()]
            if sc_alerts:
                a = sc_alerts[0]
                return f"😱 SCREAM ALERT: {a['message']} | Score {a['score']}"
            return "No active scream detections. Audio analysis running continuously."

        # Camera / surveillance
        if any(w in msg for w in ["camera","cctv","video","feed","surveillance","watch"]):
            return (f"📷 {8} camera feeds active. OpenCV detection running — "
                    f"faces, persons, and object shapes monitored. "
                    f"Last detection: logged in database.")

        # Patrol / units
        if any(w in msg for w in ["patrol","unit","deploy","send","dispatch","where"]):
            top = zones[0]
            return (f"🚗 Recommend deploying UNIT-7 + UNIT-3 to SECTOR {top['sector']} "
                    f"({top['risk_level']}, score {top['risk_score']}). "
                    f"DRONE-2 available for aerial coverage.")

        # Map / location
        if any(w in msg for w in ["map","location","gps","coordinate","position"]):
            return (f"🗺️ GPS tracking active. 5 units on patrol. "
                    f"Highest activity: Sector {zones[0]['sector']}. "
                    f"Open GPS Map page for live interactive view.")

        # Notification / SMS
        if any(w in msg for w in ["sms","email","alert","notify","send","message"]):
            return ("📱 Notification system ready. Twilio SMS and SMTP email configured. "
                    "Go to Emergency Alerts page to dispatch. "
                    "Auto-dispatch active for CRITICAL level threats.")

        # Model / AI
        if any(w in msg for w in ["model","accuracy","ai","detect","precision","recall","auc"]):
            rows, metrics = B.run_anomaly_detection(B.generate_sensor_readings(100))
            return (f"🧠 Model stats — AUC-ROC: {metrics['auc_roc']} | "
                    f"Accuracy: {metrics['accuracy']} | "
                    f"Precision: {metrics['precision']} | Recall: {metrics['recall']} | "
                    f"F1: {metrics['f1']}")

        # Hello
        if any(w in msg for w in ["hello","hi","hey","help","start","what","who"]):
            return (f"👋 SENTINEL AI online. {stats.get('unresolved',0)} unresolved alerts. "
                    f"Highest risk: {zones[0]['sector']} ({zones[0]['risk_level']}). "
                    f"Ask me: threats · last alert · risk zones · patrol · statistics · camera · model")

        # Default
        return (f"📡 Query received. System status: {stats.get('unresolved',0)} unresolved alerts. "
                f"Top zone: SECTOR {zones[0]['sector']} ({zones[0]['risk_level']}). "
                f"For specific intel, ask about: threats / alerts / zones / patrol / camera / model.")

    # ── Main entry point ──────────────────────────────────────────────────────
    def respond(self, session_id: str, message: str,
                provider: str = "rule", api_key: Optional[str] = None) -> dict:
        """
        Route to appropriate AI provider and save to DB.
        provider: "claude" | "openai" | "rule"
        """
        save_chat(session_id, "user", message)

        if provider == "claude":
            result = self.call_claude(session_id, message, api_key)
        elif provider == "openai":
            result = self.call_openai(session_id, message, api_key)
        else:
            result = {"success": True, "response": self._rule_based(message),
                      "provider": "Rule-based", "model": "sentinel-rules-v1"}

        response_text = result.get("response","")
        save_chat(session_id, "assistant", response_text)

        return {
            **result,
            "session_id": session_id,
            "timestamp":  datetime.now().isoformat(),
            "message":    message,
        }

    def get_history(self, session_id: str, limit: int = 50) -> list:
        return get_chat_history(session_id, limit)

    def clear_history(self, session_id: str) -> dict:
        from database.db import get_conn
        conn = get_conn()
        conn.execute("DELETE FROM chatbot_logs WHERE session_id=?", (session_id,))
        conn.commit()
        conn.close()
        return {"success": True, "session_id": session_id}


# ─── Singleton ────────────────────────────────────────────────────────────────
chatbot_service = ChatbotService()
