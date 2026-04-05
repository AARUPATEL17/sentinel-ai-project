"""
pages_src/chatbot.py
AI Chatbot for Officers — powered by Anthropic Claude API (or OpenAI).
Has full DB context: alerts, locations, risk zones.
Answers tactical questions in real-time.
"""
import streamlit as st
import sys, os, json, uuid, random
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db import save_chat, get_chat_history, get_alert_stats, get_alerts
from api.client import get_alerts as api_get_alerts, get_alert_stats as api_stats, ai_threat_analysis
import backend as B

def show():
    st.markdown("""
    <div style="margin-bottom:24px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 05 — AI ASSISTANT</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">OFFICER CHATBOT</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:8px;font-weight:300;max-width:640px;line-height:1.7;">
        Ask about threats, alerts, risk zones, and get tactical intelligence. Powered by Claude AI.
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Session ───────────────────────────────────────────────────────────────
    if "chat_session" not in st.session_state:
        st.session_state.chat_session = str(uuid.uuid4())[:8]
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "api_key"       not in st.session_state:
        st.session_state.api_key = ""

    session_id = st.session_state.chat_session

    # ── Config sidebar ────────────────────────────────────────────────────────
    with st.expander("⚙️  AI PROVIDER SETTINGS", expanded=len(st.session_state.api_key)==0):
        provider = st.selectbox("AI Provider", ["Claude (Anthropic)","OpenAI GPT-4","Rule-based (no API key)"])
        api_key  = st.text_input("API Key", type="password",
                                  placeholder="sk-ant-... or sk-...",
                                  value=st.session_state.api_key)
        if api_key: st.session_state.api_key = api_key
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:#5d8a99;line-height:1.8;">
          Claude: get key at <span style="color:#00e5ff;">console.anthropic.com</span><br>
          OpenAI: get key at <span style="color:#00e5ff;">platform.openai.com</span><br>
          No key: uses smart rule-based responses
        </div>""", unsafe_allow_html=True)

    # ── Build live DB context for AI ──────────────────────────────────────────
    def build_context() -> str:
        stats  = api_stats()
        alerts = api_get_alerts(limit=5, resolved=0)
        zones  = B.predict_risk_zones()[:3]
        analysis = ai_threat_analysis()
        return f"""You are SENTINEL AI, a military-grade border surveillance intelligence assistant.
You have LIVE access to the following real-time data:

ALERT STATISTICS:
- Total alerts: {stats.get('total',0)}
- Critical alerts: {stats.get('critical',0)}
- Unresolved: {stats.get('unresolved',0)}
- Today: {stats.get('today',0)}

ACTIVE THREATS (top 5 unresolved):
{json.dumps([{"level":a["level"],"type":a["type"],"sector":a["sector"],"message":a["message"],"time":a["created_at"]} for a in alerts], indent=2)}

TOP RISK ZONES:
{json.dumps([{"sector":z["sector"],"risk_level":z["risk_level"],"risk_score":z["risk_score"]} for z in zones], indent=2)}

AI ANALYSIS:
- Anomaly rate: {analysis.get('anomaly_rate',0)*100:.1f}%
- Model AUC: {analysis.get('model_auc',0)}
- Top risk sector: {analysis.get('top_risk_sector','N/A')} (score: {analysis.get('top_risk_score',0)})
- Active threat count: {analysis.get('active_threats',0)}

CURRENT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

You MUST answer concisely in a military/tactical tone.
Give specific data from the context above when asked.
For unknown info, say "Data not available in current feed."
"""

    # ── Rule-based fallback (no API key) ──────────────────────────────────────
    def rule_based_response(user_msg: str) -> str:
        msg = user_msg.lower()
        stats  = api_stats()
        alerts = api_get_alerts(limit=3, resolved=0)
        zones  = B.predict_risk_zones()[:3]

        if any(w in msg for w in ["threat","danger","critical","alert"]):
            top = [a for a in alerts if a["level"]=="CRITICAL"]
            if top:
                a = top[0]
                return (f"🔴 CRITICAL ALERT ACTIVE: {a['message']} | "
                        f"Sector {a['sector']} | Source: {a['source']} | "
                        f"Score: {a['score']} | Time: {a['created_at']}")
            return f"📊 {stats.get('unresolved',0)} unresolved alerts. No CRITICAL active right now."

        if any(w in msg for w in ["last alert","recent","latest"]):
            if alerts:
                a = alerts[0]
                return (f"Last alert — [{a['level']}] {a['message']} | "
                        f"Sector {a['sector']} | {a['created_at'][:16]}")
            return "No recent alerts in the database."

        if any(w in msg for w in ["risk","zone","sector","dangerous"]):
            z = zones[0]
            return (f"⚠️ Highest risk: SECTOR {z['sector']} — {z['risk_level']} "
                    f"(score {z['risk_score']}). "
                    f"Also monitoring: {zones[1]['sector']} ({zones[1]['risk_level']}), "
                    f"{zones[2]['sector']} ({zones[2]['risk_level']}).")

        if any(w in msg for w in ["how many","count","total","statistics","stats"]):
            return (f"📊 Database summary: {stats.get('total',0)} total alerts | "
                    f"{stats.get('critical',0)} critical | "
                    f"{stats.get('unresolved',0)} unresolved | "
                    f"{stats.get('today',0)} today.")

        if any(w in msg for w in ["gunshot","shot","weapon","gun"]):
            return ("🔫 Audio analysis running. Gunshot detection uses zero-crossing rate + "
                    "spectral centroid analysis. Any confirmed gunshot events are escalated to CRITICAL.")

        if any(w in msg for w in ["camera","cctv","video","surveillance"]):
            return ("📷 Camera surveillance active. OpenCV Haar Cascades detecting faces, "
                    "bodies, and object shapes. Anomalies trigger CCTV alerts in the database.")

        if any(w in msg for w in ["patrol","unit","dispatch","send"]):
            return ("🚗 Patrol recommendation: Deploy UNIT-7 to highest-risk sector. "
                    f"Current hot zone: SECTOR {zones[0]['sector']} ({zones[0]['risk_level']}).")

        if any(w in msg for w in ["hello","hi","hey","help"]):
            return ("👋 SENTINEL AI online. I can answer:\n"
                    "• What threats are detected?\n"
                    "• Show last alert\n"
                    "• Which sector is highest risk?\n"
                    "• How many alerts today?\n"
                    "• Recommend patrol deployment")

        return (f"Query processed. Current status: {stats.get('unresolved',0)} unresolved alerts. "
                f"Highest risk: Sector {zones[0]['sector']} ({zones[0]['risk_level']}). "
                "For more details, ask a specific question.")

    # ── Claude API call ───────────────────────────────────────────────────────
    def call_claude(messages_history, user_msg, api_key, context) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msgs = [{"role":m["role"],"content":m["content"]}
                    for m in messages_history[-8:] if m["role"] in ("user","assistant")]
            msgs.append({"role":"user","content":user_msg})
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                system=context,
                messages=msgs,
            )
            return resp.content[0].text
        except ImportError:
            return "❌ Install anthropic: `pip install anthropic`"
        except Exception as e:
            return f"❌ Claude API error: {e}"

    def call_openai(messages_history, user_msg, api_key, context) -> str:
        try:
            import openai
            openai.api_key = api_key
            msgs = [{"role":"system","content":context}]
            for m in messages_history[-8:]:
                if m["role"] in ("user","assistant"):
                    msgs.append({"role":m["role"],"content":m["content"]})
            msgs.append({"role":"user","content":user_msg})
            resp = openai.chat.completions.create(model="gpt-4o-mini", messages=msgs, max_tokens=512)
            return resp.choices[0].message.content
        except ImportError:
            return "❌ Install openai: `pip install openai`"
        except Exception as e:
            return f"❌ OpenAI error: {e}"

    # ── Display chat history ──────────────────────────────────────────────────
    st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
        letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">▸ CHAT — SESSION {}</div>""".format(session_id),
        unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_messages:
            st.markdown("""
            <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);padding:20px;margin-bottom:8px;">
              <div style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#00e5ff;">
                🤖 SENTINEL AI — Online</div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:12px;color:#5d8a99;
                          line-height:1.9;margin-top:8px;">
                I have live access to your threat database. Try asking:<br>
                <span style="color:#ffd600;">• "What threats are detected right now?"</span><br>
                <span style="color:#ffd600;">• "Show me the last alert"</span><br>
                <span style="color:#ffd600;">• "Which sector is most dangerous?"</span><br>
                <span style="color:#ffd600;">• "How many alerts today?"</span><br>
                <span style="color:#ffd600;">• "Recommend patrol deployment"</span>
              </div>
            </div>""", unsafe_allow_html=True)

        for msg in st.session_state.chat_messages:
            is_user = msg["role"] == "user"
            bg   = "rgba(0,229,255,0.05)" if is_user else "rgba(255,107,53,0.05)"
            bdr  = "rgba(0,229,255,0.2)"  if is_user else "rgba(255,107,53,0.2)"
            name = "👮 OFFICER" if is_user else "🤖 SENTINEL AI"
            nc   = "#00e5ff" if is_user else "#ff6b35"
            st.markdown(f"""
            <div style="background:{bg};border-left:3px solid {bdr};padding:14px 18px;margin-bottom:8px;">
              <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:3px;
                          color:{nc};margin-bottom:6px;">{name} · {msg.get('time','')}</div>
              <div style="font-family:'Barlow',sans-serif;font-size:14px;color:#cce8f0;line-height:1.7;
                          white-space:pre-wrap;">{msg['content']}</div>
            </div>""", unsafe_allow_html=True)

    # ── Input ─────────────────────────────────────────────────────────────────
    col_q, col_btn = st.columns([5,1])
    user_input = col_q.text_input("Ask SENTINEL AI...", key="chat_input",
                                   placeholder="What threat is detected? / Show last alert / Risk zones?",
                                   label_visibility="collapsed")
    send_btn   = col_btn.button("SEND ▶", use_container_width=True, type="primary")

    # Quick-ask buttons
    qa_cols = st.columns(4)
    quick_asks = ["What threats are detected?","Show last alert","Highest risk sector?","How many alerts today?"]
    quick_input = None
    for col, qa in zip(qa_cols, quick_asks):
        if col.button(qa, use_container_width=True, key=f"qa_{qa}"):
            quick_input = qa

    final_input = quick_input or (user_input if send_btn else None)

    if final_input and final_input.strip():
        # Add user message
        user_msg_obj = {"role":"user","content":final_input.strip(),
                        "time": datetime.now().strftime("%H:%M:%S")}
        st.session_state.chat_messages.append(user_msg_obj)
        save_chat(session_id, "user", final_input.strip())

        # Generate response
        context = build_context()
        with st.spinner("🤖 SENTINEL AI processing..."):
            key = st.session_state.api_key.strip()
            if key and "claude" in provider.lower():
                response = call_claude(st.session_state.chat_messages, final_input, key, context)
            elif key and "openai" in provider.lower():
                response = call_openai(st.session_state.chat_messages, final_input, key, context)
            else:
                response = rule_based_response(final_input)

        ai_msg_obj = {"role":"assistant","content":response,
                      "time": datetime.now().strftime("%H:%M:%S")}
        st.session_state.chat_messages.append(ai_msg_obj)
        save_chat(session_id, "assistant", response)
        st.rerun()

    # ── Controls ──────────────────────────────────────────────────────────────
    cc1, cc2 = st.columns(2)
    if cc1.button("🗑️ CLEAR CONVERSATION", use_container_width=True):
        st.session_state.chat_messages = []
        st.session_state.chat_session  = str(uuid.uuid4())[:8]
        st.rerun()

    if cc2.button("📋 EXPORT CHAT LOG", use_container_width=True):
        log_text = "\n".join(
            f"[{m['time']}] {'OFFICER' if m['role']=='user' else 'AI'}: {m['content']}"
            for m in st.session_state.chat_messages
        )
        st.download_button("⬇ Download", log_text, "sentinel_chat_log.txt", "text/plain")
