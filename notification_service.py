"""
api/services/notification_service.py
──────────────────────────────────────
Backend service for ALL notifications:
  • SMS  via Twilio REST API
  • Email via SMTP (Gmail / SendGrid)
  • Push  (webhook / browser push stub)

Usage:
    svc = NotificationService(config)
    svc.send_sms("+91XXXXXXXXXX", "Alert: Gunshot detected")
    svc.send_email("officer@gov.in", "CRITICAL ALERT", body)
    svc.dispatch_alert(alert_dict)   # auto-routes by level
"""

import smtplib, os, json, time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Load .env if python-dotenv installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
from database.db import log_notification


class NotificationService:
    """
    Centralised notification dispatcher.
    Reads credentials from environment variables or passed config dict.
    """

    def __init__(self, config: Optional[dict] = None):
        cfg = config or {}
        # Twilio
        self.twilio_sid    = cfg.get("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_ACCOUNT_SID","")
        self.twilio_token  = cfg.get("TWILIO_AUTH_TOKEN")  or os.getenv("TWILIO_AUTH_TOKEN","")
        self.twilio_from   = cfg.get("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_FROM_NUMBER","")
        self.default_sms_to= cfg.get("TWILIO_TO_NUMBER")   or os.getenv("TWILIO_TO_NUMBER","")
        # SMTP
        self.smtp_host     = cfg.get("SMTP_HOST") or os.getenv("SMTP_HOST","smtp.gmail.com")
        self.smtp_port     = int(cfg.get("SMTP_PORT") or os.getenv("SMTP_PORT","587"))
        self.smtp_user     = cfg.get("SMTP_USER") or os.getenv("SMTP_USER","")
        self.smtp_pass     = cfg.get("SMTP_PASS") or os.getenv("SMTP_PASS","")
        self.default_email = cfg.get("ALERT_EMAIL_TO") or os.getenv("ALERT_EMAIL_TO","")

    # ── SMS ───────────────────────────────────────────────────────────────────
    def send_sms(self, to: str, message: str, alert_id: int = 0) -> dict:
        """
        Send SMS via Twilio REST API.
        Requires: pip install twilio
        Fallback: logs as simulated.
        """
        if not self.twilio_sid or not self.twilio_token:
            result = {"success": True, "simulated": True,
                      "reason": "No Twilio credentials configured",
                      "would_send_to": to, "message": message[:100]}
            log_notification(alert_id, "sms", to, "simulated")
            return result

        try:
            from twilio.rest import Client
            client = Client(self.twilio_sid, self.twilio_token)
            msg    = client.messages.create(
                body=message, from_=self.twilio_from, to=to
            )
            log_notification(alert_id, "sms", to, "sent")
            return {"success": True, "simulated": False, "sid": msg.sid,
                    "to": to, "status": msg.status}
        except ImportError:
            log_notification(alert_id, "sms", to, "failed", "twilio not installed")
            return {"success": False, "error": "pip install twilio",
                    "simulated": True, "would_send_to": to}
        except Exception as e:
            log_notification(alert_id, "sms", to, "failed", str(e))
            return {"success": False, "error": str(e)}

    # ── Email ─────────────────────────────────────────────────────────────────
    def send_email(self, to: str, subject: str, body: str,
                   alert_id: int = 0, html: Optional[str] = None) -> dict:
        """
        Send email via SMTP.
        Uses Gmail by default. Works with any SMTP server.
        For SendGrid: host=smtp.sendgrid.net, port=587, user='apikey', pass=<api_key>
        """
        if not self.smtp_user or not self.smtp_pass:
            log_notification(alert_id, "email", to, "simulated")
            return {"success": True, "simulated": True,
                    "reason": "No SMTP credentials configured",
                    "would_send_to": to, "subject": subject}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = self.smtp_user
            msg["To"]      = to
            msg.attach(MIMEText(body, "plain"))
            if html:
                msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, to, msg.as_string())

            log_notification(alert_id, "email", to, "sent")
            return {"success": True, "simulated": False, "to": to, "subject": subject}

        except Exception as e:
            log_notification(alert_id, "email", to, "failed", str(e))
            return {"success": False, "error": str(e)}

    # ── HTML Email template ───────────────────────────────────────────────────
    @staticmethod
    def build_alert_email_html(alert: dict) -> str:
        level  = alert.get("level","UNKNOWN")
        colors = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","LOW":"#39ff14"}
        color  = colors.get(level,"#cce8f0")
        return f"""
        <html><body style="background:#020b0f;color:#cce8f0;font-family:monospace;padding:24px;">
          <div style="max-width:600px;margin:0 auto;border:1px solid {color};padding:24px;">
            <h1 style="color:{color};letter-spacing:4px;font-size:28px;">
              🚨 SENTINEL ALERT</h1>
            <table style="width:100%;border-collapse:collapse;margin-top:16px;">
              <tr><td style="color:#5d8a99;padding:6px;">LEVEL</td>
                  <td style="color:{color};font-weight:bold;padding:6px;">{level}</td></tr>
              <tr><td style="color:#5d8a99;padding:6px;">TYPE</td>
                  <td style="padding:6px;">{alert.get('type','N/A')}</td></tr>
              <tr><td style="color:#5d8a99;padding:6px;">SECTOR</td>
                  <td style="padding:6px;">{alert.get('sector','N/A')}</td></tr>
              <tr><td style="color:#5d8a99;padding:6px;">MESSAGE</td>
                  <td style="padding:6px;">{alert.get('message','')}</td></tr>
              <tr><td style="color:#5d8a99;padding:6px;">SCORE</td>
                  <td style="padding:6px;">{alert.get('score',0)}</td></tr>
              <tr><td style="color:#5d8a99;padding:6px;">TIME</td>
                  <td style="padding:6px;">{alert.get('created_at','')}</td></tr>
              <tr><td style="color:#5d8a99;padding:6px;">SOURCE</td>
                  <td style="padding:6px;">{alert.get('source','N/A')}</td></tr>
            </table>
            <div style="margin-top:24px;padding-top:16px;border-top:1px solid {color};
                        color:#5d8a99;font-size:11px;letter-spacing:2px;">
              SENTINEL BORDER DEFENCE AI PLATFORM · AUTOMATED DISPATCH
            </div>
          </div>
        </body></html>"""

    # ── SMS template ──────────────────────────────────────────────────────────
    @staticmethod
    def build_alert_sms(alert: dict) -> str:
        icons = {"CRITICAL":"🔴","HIGH":"🟡","MEDIUM":"🟠","LOW":"🟢"}
        icon  = icons.get(alert.get("level",""), "⚠")
        return (f"{icon} SENTINEL [{alert.get('level','')}] "
                f"SEC {alert.get('sector','')} | "
                f"{alert.get('message','')[:80]} | "
                f"Score:{alert.get('score',0)} | "
                f"{alert.get('created_at','')[:16]}")

    # ── Auto-dispatch ─────────────────────────────────────────────────────────
    def dispatch_alert(self, alert: dict,
                       sms_to: Optional[str] = None,
                       email_to: Optional[str] = None) -> dict:
        """
        Automatically dispatch alert via appropriate channels based on severity.
        CRITICAL → SMS + Email
        HIGH     → Email
        MEDIUM   → Email (if configured)
        LOW      → Log only
        """
        level    = alert.get("level","LOW")
        alert_id = alert.get("id", 0)
        results  = {"level": level, "channels": []}

        sms_recipient   = sms_to   or self.default_sms_to
        email_recipient = email_to or self.default_email

        if level == "CRITICAL":
            if sms_recipient:
                sms_result = self.send_sms(
                    sms_recipient,
                    self.build_alert_sms(alert),
                    alert_id
                )
                results["channels"].append({"channel":"sms","result":sms_result})

            if email_recipient:
                email_result = self.send_email(
                    email_recipient,
                    f"🔴 SENTINEL CRITICAL ALERT — {alert.get('sector','')}",
                    f"CRITICAL ALERT\n{json.dumps(alert, indent=2)}",
                    alert_id,
                    html=self.build_alert_email_html(alert)
                )
                results["channels"].append({"channel":"email","result":email_result})

        elif level == "HIGH":
            if email_recipient:
                email_result = self.send_email(
                    email_recipient,
                    f"🟡 SENTINEL HIGH ALERT — {alert.get('sector','')}",
                    f"HIGH ALERT\n{json.dumps(alert, indent=2)}",
                    alert_id,
                    html=self.build_alert_email_html(alert)
                )
                results["channels"].append({"channel":"email","result":email_result})

        elif level == "MEDIUM":
            if email_recipient:
                email_result = self.send_email(
                    email_recipient,
                    f"🟠 SENTINEL MEDIUM ALERT — {alert.get('sector','')}",
                    f"MEDIUM ALERT\n{json.dumps(alert, indent=2)}",
                    alert_id
                )
                results["channels"].append({"channel":"email","result":email_result})
        else:
            log_notification(alert_id, "log", "system", "logged_only")
            results["channels"].append({"channel":"log","result":{"success":True}})

        results["dispatched_at"] = datetime.now().isoformat()
        return results


# ─── Module-level singleton ───────────────────────────────────────────────────
notification_service = NotificationService()
