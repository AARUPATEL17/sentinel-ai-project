"""
pages_src/emergency_alerts.py
Emergency Alert System — SMS (Twilio) + Email (SMTP) + Auto-Alert
"""
import streamlit as st
import sys, os, smtplib, random
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.client import get_alerts, resolve_alert, create_alert, send_sms, send_email
from database.db import get_notification_logs, log_notification

def show():
    st.markdown("""
    <div style="margin-bottom:24px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 04 — EMERGENCY SYSTEM</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">ALERT DISPATCH</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:8px;font-weight:300;max-width:640px;line-height:1.7;">
        Send real SMS via Twilio and Email via SMTP. Configure credentials below to activate live sending.
      </div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["📱 SMS ALERTS","📧 EMAIL ALERTS","⚡ AUTO-DISPATCH","📋 NOTIFICATION LOG","⚙️ CREDENTIALS"])

    # ── SMS ───────────────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:16px;">▸ SEND SMS VIA TWILIO API</div>""",
            unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        sms_to   = col1.text_input("Recipient Phone", "+91XXXXXXXXXX")
        sms_from = col2.text_input("Twilio Number",   "+1XXXXXXXXXX")
        sms_sid  = col1.text_input("Twilio Account SID", type="password",
                                   placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        sms_tok  = col2.text_input("Twilio Auth Token",  type="password",
                                   placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

        alerts = get_alerts(limit=10)
        alert_choices = {f"[{a['level']}] {a['message'][:50]}": a for a in alerts[:10]}
        chosen_label  = st.selectbox("Select Alert to dispatch", list(alert_choices.keys()))
        chosen_alert  = alert_choices.get(chosen_label)

        custom_msg = st.text_area("Custom message (or auto from alert)",
            value=f"🚨 SENTINEL ALERT [{chosen_alert['level'] if chosen_alert else ''}]: "
                  f"{chosen_alert['message'][:100] if chosen_alert else ''} — {datetime.now().strftime('%H:%M')}",
            height=80)

        bc1, bc2 = st.columns(2)
        if bc1.button("📱 SEND REAL SMS (Twilio)", use_container_width=True, type="primary"):
            if sms_sid and sms_tok and sms_to and sms_from:
                try:
                    from twilio.rest import Client
                    client = Client(sms_sid, sms_tok)
                    msg = client.messages.create(body=custom_msg, from_=sms_from, to=sms_to)
                    aid = chosen_alert["id"] if chosen_alert else 0
                    log_notification(aid, "sms", sms_to, "sent")
                    st.success(f"✅ SMS sent! SID: {msg.sid}")
                except ImportError:
                    st.error("❌ Install Twilio: `pip install twilio`")
                except Exception as e:
                    log_notification(0, "sms", sms_to, "failed", str(e))
                    st.error(f"❌ Twilio error: {e}")
            else:
                st.warning("⚠️ Fill all Twilio credentials to send real SMS")

        if bc2.button("📝 LOG SIMULATED SMS", use_container_width=True):
            aid = chosen_alert["id"] if chosen_alert else 0
            log_notification(aid, "sms", sms_to, "simulated")
            st.success("✅ Logged as simulated (no Twilio credentials used)")

        # Twilio setup guide
        with st.expander("📖 How to get Twilio credentials"):
            st.markdown("""
            <div style="font-family:'Share Tech Mono',monospace;font-size:12px;line-height:2;color:#5d8a99;">
            1. Sign up at <span style="color:#00e5ff;">twilio.com</span> (free trial available)<br>
            2. Go to Console → Account Info → copy <span style="color:#ffd600;">Account SID</span> and <span style="color:#ffd600;">Auth Token</span><br>
            3. Get a Twilio phone number (free trial gives 1 number)<br>
            4. Install: <span style="color:#39ff14;">pip install twilio</span><br>
            5. Verify your recipient phone number in the Twilio console<br>
            6. Enter credentials above and click SEND REAL SMS
            </div>""", unsafe_allow_html=True)

    # ── Email ─────────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:16px;">▸ SEND EMAIL VIA SMTP</div>""",
            unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        smtp_host = col1.text_input("SMTP Host", "smtp.gmail.com")
        smtp_port = col2.number_input("SMTP Port", value=587, step=1)
        smtp_user = col1.text_input("SMTP Username (your Gmail)", "your@gmail.com")
        smtp_pass = col2.text_input("SMTP Password / App Password", type="password")
        email_to  = col1.text_input("Recipient Email", "officer@sentinel.gov")
        email_subj = col2.text_input("Subject", f"🚨 SENTINEL ALERT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        alerts = get_alerts(limit=10)
        chosen2 = st.selectbox("Select Alert", [f"[{a['level']}] {a['message'][:60]}" for a in alerts[:10]],
                                key="email_alert_select")
        idx = [f"[{a['level']}] {a['message'][:60]}" for a in alerts[:10]].index(chosen2) if alerts else 0
        sel_alert = alerts[idx] if alerts else None

        email_body = st.text_area("Email Body", height=120, value=f"""SENTINEL BORDER DEFENCE SYSTEM
════════════════════════════════
ALERT LEVEL : {sel_alert['level'] if sel_alert else 'N/A'}
TYPE        : {sel_alert['type']  if sel_alert else 'N/A'}
SECTOR      : {sel_alert['sector'] if sel_alert else 'N/A'}
MESSAGE     : {sel_alert['message'] if sel_alert else 'N/A'}
TIME        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
SCORE       : {sel_alert['score'] if sel_alert else 'N/A'}
════════════════════════════════
Please respond immediately.
SENTINEL AUTOMATED DISPATCH""")

        bc1, bc2 = st.columns(2)
        if bc1.button("📧 SEND REAL EMAIL", use_container_width=True, type="primary"):
            if smtp_user and smtp_pass and email_to:
                try:
                    msg = MIMEMultipart()
                    msg["From"]    = smtp_user
                    msg["To"]      = email_to
                    msg["Subject"] = email_subj
                    msg.attach(MIMEText(email_body,"plain"))
                    with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.sendmail(smtp_user, email_to, msg.as_string())
                    aid = sel_alert["id"] if sel_alert else 0
                    log_notification(aid, "email", email_to, "sent")
                    st.success(f"✅ Email sent to {email_to}")
                except Exception as e:
                    log_notification(0, "email", email_to, "failed", str(e))
                    st.error(f"❌ Email error: {e}")
            else:
                st.warning("⚠️ Fill SMTP credentials to send real email")

        if bc2.button("📝 LOG SIMULATED EMAIL", use_container_width=True):
            aid = sel_alert["id"] if sel_alert else 0
            log_notification(aid, "email", email_to, "simulated")
            st.success("✅ Logged as simulated")

        with st.expander("📖 Gmail App Password Setup"):
            st.markdown("""
            <div style="font-family:'Share Tech Mono',monospace;font-size:12px;line-height:2;color:#5d8a99;">
            Gmail requires App Password (not your main password):<br>
            1. Google Account → Security → 2-Step Verification → Enable<br>
            2. Security → App Passwords → Generate for "Mail"<br>
            3. Use the 16-character code as SMTP Password above<br>
            4. SMTP Host: <span style="color:#00e5ff;">smtp.gmail.com</span> · Port: <span style="color:#ffd600;">587</span>
            </div>""", unsafe_allow_html=True)

    # ── Auto-Dispatch ─────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:16px;">▸ AUTO-DISPATCH RULES</div>""",
            unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        auto_sms_on_critical  = col1.checkbox("📱 Auto SMS on CRITICAL", value=True)
        auto_email_on_high    = col2.checkbox("📧 Auto Email on HIGH+",  value=True)
        auto_sms_to  = col1.text_input("Default SMS recipient",   "+91XXXXXXXXXX", key="auto_sms")
        auto_email_to= col2.text_input("Default Email recipient", "commander@sentinel.gov", key="auto_email")

        if st.button("⚡ RUN AUTO-DISPATCH CHECK NOW", type="primary", use_container_width=True):
            alerts = get_alerts(limit=20, resolved=0)
            critical = [a for a in alerts if a["level"]=="CRITICAL"]
            high     = [a for a in alerts if a["level"] in ("CRITICAL","HIGH")]
            sms_sent = email_sent = 0

            for a in critical[:3]:
                result = send_sms(auto_sms_to,
                    f"🚨 CRITICAL: {a['message']} | Sector {a['sector']} | {a['created_at']}", a["id"])
                sms_sent += 1

            for a in high[:3]:
                result = send_email(auto_email_to,
                    f"SENTINEL [{a['level']}] {a['sector']}",
                    f"Alert: {a['message']}\nLevel: {a['level']}\nSector: {a['sector']}\nTime: {a['created_at']}", a["id"])
                email_sent += 1

            st.success(f"✅ Auto-dispatched: {sms_sent} SMS, {email_sent} Emails (simulated — add credentials for real)")

            # Show what was dispatched
            if critical or high:
                rows_html = ""
                lc = {"CRITICAL":"#ff1744","HIGH":"#ffd600"}
                for a in (critical+high)[:6]:
                    c = lc.get(a["level"],"#cce8f0")
                    rows_html += f"""<div style="display:grid;grid-template-columns:70px 80px 1fr;gap:8px;
                        padding:8px 14px;border-left:3px solid {c};background:rgba(0,0,0,0.3);margin-bottom:2px;
                        font-family:'Share Tech Mono',monospace;font-size:11px;">
                        <span style="color:{c};">{a['level']}</span>
                        <span style="color:#5d8a99;">SEC {a['sector']}</span>
                        <span style="color:#cce8f0;">{a['message'][:70]}</span></div>"""
                st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:8px;margin-top:8px;">{rows_html}</div>',
                            unsafe_allow_html=True)

    # ── Notification log ──────────────────────────────────────────────────────
    with tabs[3]:
        logs = get_notification_logs(30)
        if not logs:
            st.info("No notifications logged yet.")
        else:
            lc_status = {"sent":"#39ff14","simulated":"#ffd600","failed":"#ff1744",
                         "simulated_local":"#ffd600","pending":"#5d8a99"}
            lc_ch = {"sms":"#00e5ff","email":"#ff6b35"}
            rows_html = ""
            for log in logs:
                cs = lc_status.get(log["status"],"#cce8f0")
                cc = lc_ch.get(log["channel"],"#cce8f0")
                rows_html += f"""<div style="display:grid;grid-template-columns:55px 60px 1fr 80px 70px;gap:8px;
                    padding:9px 14px;border-left:3px solid {cs};background:rgba(0,0,0,0.3);margin-bottom:2px;
                    font-family:'Share Tech Mono',monospace;font-size:11px;">
                    <span style="color:{cc};">{log['channel'].upper()}</span>
                    <span style="color:{cs};">{log['status'].upper()}</span>
                    <span style="color:#cce8f0;">{log['recipient']}</span>
                    <span style="color:#5d8a99;">{log.get('created_at','')[:16]}</span>
                    <span style="color:#5d8a99;">AID:{log.get('alert_id','-')}</span></div>"""
            st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:8px;">{rows_html}</div>',
                        unsafe_allow_html=True)

    # ── Credentials guide ─────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:24px;
                    font-family:'Share Tech Mono',monospace;font-size:12px;line-height:2.2;color:#5d8a99;">
          <div style="color:#00e5ff;font-size:14px;letter-spacing:2px;margin-bottom:16px;">CREDENTIALS SETUP GUIDE</div>

          <div style="color:#ffd600;margin-bottom:4px;">📱 TWILIO (SMS)</div>
          pip install twilio<br>
          Account SID → twilio.com/console<br>
          Auth Token  → twilio.com/console<br>
          From Number → Buy/get free trial number<br><br>

          <div style="color:#ffd600;margin-bottom:4px;">📧 SMTP (Email)</div>
          Gmail: Host=smtp.gmail.com Port=587<br>
          Use App Password (not main password)<br>
          Enable 2FA → Google Account → Security<br><br>

          <div style="color:#ffd600;margin-bottom:4px;">⚠️ IMPORTANT</div>
          <span style="color:#ff1744;">NEVER commit credentials to git/GitHub</span><br>
          Store in <span style="color:#39ff14;">.env</span> file and use <span style="color:#39ff14;">python-dotenv</span>:<br>
          <span style="color:#39ff14;">TWILIO_SID=ACxxx</span><br>
          <span style="color:#39ff14;">TWILIO_TOKEN=xxx</span><br>
          <span style="color:#39ff14;">SMTP_PASS=xxx</span>
        </div>""", unsafe_allow_html=True)
