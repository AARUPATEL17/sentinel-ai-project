"""
SENTINEL v3.0 — Border Defence AI Platform
Full-stack: Streamlit UI + Flask API + SQLite DB
Run: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="SENTINEL — Border Defence AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;600;700;900&family=Barlow:wght@300;400;500&display=swap');

:root {
  --bg:#020b0f; --panel:#061520; --panel2:#081c28;
  --accent:#00e5ff; --accent2:#ff6b35; --accent3:#39ff14;
  --warn:#ffd600; --danger:#ff1744;
  --text:#cce8f0; --dim:#5d8a99;
  --mono:'Share Tech Mono',monospace;
  --display:'Barlow Condensed',sans-serif;
}
#MainMenu,footer,header,.stDeployButton{visibility:hidden;}
.stApp{
  background:#020b0f !important;
  background-image:linear-gradient(rgba(0,229,255,0.025) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,229,255,0.025) 1px,transparent 1px) !important;
  background-size:40px 40px !important;
  font-family:'Barlow',sans-serif; color:#cce8f0;
}
[data-testid="stSidebar"]{background:#040f15 !important;border-right:1px solid rgba(0,229,255,0.12) !important;}
[data-testid="stSidebar"] *{color:#cce8f0 !important;}
[data-testid="metric-container"]{background:#061520 !important;border:1px solid rgba(0,229,255,0.15) !important;
  border-radius:0 !important;clip-path:polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,8px 100%,0 calc(100% - 8px));}
[data-testid="metric-container"] label{color:#5d8a99 !important;font-family:'Share Tech Mono',monospace !important;
  font-size:10px !important;letter-spacing:2px !important;text-transform:uppercase !important;}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00e5ff !important;
  font-family:'Barlow Condensed',sans-serif !important;font-weight:900 !important;}
.stButton>button{background:transparent !important;border:1px solid rgba(0,229,255,0.3) !important;
  color:#00e5ff !important;font-family:'Barlow Condensed',sans-serif !important;font-weight:700 !important;
  letter-spacing:3px !important;text-transform:uppercase !important;border-radius:0 !important;
  clip-path:polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,8px 100%,0 calc(100% - 8px)) !important;}
.stButton>button:hover{background:rgba(0,229,255,0.08) !important;border-color:#00e5ff !important;
  box-shadow:0 0 20px rgba(0,229,255,0.2) !important;}
.stButton>[data-testid="baseButton-primary"]{background:#00e5ff !important;color:#000 !important;
  border-color:#00e5ff !important;}
.stTabs [data-baseweb="tab-list"]{background:#040f15 !important;border-bottom:1px solid rgba(0,229,255,0.12) !important;gap:0 !important;}
.stTabs [data-baseweb="tab"]{background:transparent !important;border-radius:0 !important;color:#5d8a99 !important;
  font-family:'Barlow Condensed',sans-serif !important;font-weight:700 !important;letter-spacing:3px !important;
  text-transform:uppercase !important;border-bottom:2px solid transparent !important;padding:10px 20px !important;}
.stTabs [aria-selected="true"]{color:#00e5ff !important;border-bottom:2px solid #00e5ff !important;}
.stSelectbox>div>div,.stMultiSelect>div>div{background:#061520 !important;border-color:rgba(0,229,255,0.15) !important;
  border-radius:0 !important;color:#cce8f0 !important;}
.stTextInput>div>div>input,.stTextArea>div>div>textarea{background:#061520 !important;
  border-color:rgba(0,229,255,0.15) !important;color:#cce8f0 !important;border-radius:0 !important;}
.stDataFrame{border:1px solid rgba(0,229,255,0.12) !important;}
[data-testid="stDataFrameResizable"] thead tr th{background:#061520 !important;color:#00e5ff !important;
  font-family:'Share Tech Mono',monospace !important;font-size:11px !important;letter-spacing:2px !important;}
[data-testid="stExpander"]{background:#061520 !important;border:1px solid rgba(0,229,255,0.1) !important;border-radius:0 !important;}
.stCheckbox>label>span{color:#cce8f0 !important;}
hr{border-color:rgba(0,229,255,0.1) !important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:#020b0f;}
::-webkit-scrollbar-thumb{background:rgba(0,229,255,0.2);}
</style>
""", unsafe_allow_html=True)

# ── Auth check ────────────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from auth import check_login, show_logout_button, is_admin

if not check_login():
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align:center;padding:20px 0 12px;">
  <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:28px;
              letter-spacing:8px;color:#00e5ff;text-shadow:0 0 20px rgba(0,229,255,0.4);">
    SENTINEL</div>
  <div style="font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:3px;
              color:#5d8a99;margin-top:3px;">BORDER DEFENCE AI v3.0</div>
  <div style="margin:12px auto;width:80%;height:1px;background:rgba(0,229,255,0.15);"></div>
</div>
""", unsafe_allow_html=True)

# Navigation
pages = [
    ("📊","Dashboard",         "Live command centre"),
    ("🔍","AI Threat Detect",  "Gunshot · Scream · Motion"),
    ("🎥","Camera Surveillance","CCTV · Object detection"),
    ("🌐","GPS Live Map",       "Real interactive map"),
    ("🚨","Emergency Alerts",  "SMS · Email dispatch"),
    ("🤖","AI Chatbot",         "Ask the AI officer"),
    ("📡","Real-Time Feed",    "Live sensor telemetry"),
    ("🗺️","Risk Map",           "Predictive zones"),
    ("📦","Datasets",          "Generate & download"),
]
if is_admin():
    pages.append(("🔐","User Management","Admin control"))

page_labels = [f"{e}  {n}" for e,n,_ in pages]
selected    = st.sidebar.radio("NAV", page_labels, label_visibility="collapsed")

# Page descriptions
for e,n,d in pages:
    if f"{e}  {n}" == selected:
        st.sidebar.markdown(f"""
        <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:2px;
                    color:#5d8a99;padding:4px 8px;">{d}</div>""", unsafe_allow_html=True)
        break

# System status
from database.db import get_alert_stats as db_stats
try:
    s = db_stats()
    crit_count = s.get("critical",0)
    unres      = s.get("unresolved",0)
    crit_color = "#ff1744" if crit_count>0 else "#39ff14"
except:
    crit_count = 0; unres = 0; crit_color = "#5d8a99"

st.sidebar.markdown(f"""
<div style="margin-top:20px;padding:14px;background:#061520;border:1px solid rgba(0,229,255,0.1);">
  <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;margin-bottom:10px;">SYSTEM STATUS</div>
  <div style="display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;font-size:10px;margin-bottom:5px;">
    <span style="color:#5d8a99;">DB Alerts</span><span style="color:#00e5ff;">{s.get('total',0)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;font-size:10px;margin-bottom:5px;">
    <span style="color:#5d8a99;">Unresolved</span><span style="color:#ffd600;">{unres}</span>
  </div>
  <div style="display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;font-size:10px;margin-bottom:5px;">
    <span style="color:#5d8a99;">Critical</span><span style="color:{crit_color};">{crit_count} {'●' if crit_count>0 else '✓'}</span>
  </div>
  <div style="display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;font-size:10px;">
    <span style="color:#5d8a99;">Sensor Net</span><span style="color:#39ff14;">2,847 ●</span>
  </div>
</div>
""", unsafe_allow_html=True)

show_logout_button()

st.sidebar.markdown("""
<div style="margin-top:12px;font-family:'Share Tech Mono',monospace;font-size:8px;
            letter-spacing:2px;color:#5d8a99;text-align:center;">
  v3.0 · SQLITE + FLASK + OPENCV<br>UNCLASSIFIED / EDU USE
</div>""", unsafe_allow_html=True)

# ── Route ─────────────────────────────────────────────────────────────────────
name = selected.split("  ",1)[1] if "  " in selected else selected

if   name == "Dashboard":
    from pages_src.main_dashboard import show; show()
elif name == "AI Threat Detect":
    from pages_src.ai_threat import show; show()
elif name == "Camera Surveillance":
    from pages_src.camera_surveillance import show; show()
elif name == "GPS Live Map":
    from pages_src.gpsmap import show; show()
elif name == "Emergency Alerts":
    from pages_src.emergency_alerts import show; show()
elif name == "AI Chatbot":
    from pages_src.chatbot import show; show()
elif name == "Real-Time Feed":
    from pages_src.realtime import show; show()
elif name == "Risk Map":
    from pages_src.riskmap import show; show()
elif name == "Datasets":
    from pages_src.datasets import show; show()
elif name == "User Management":
    from auth import show_user_management; show_user_management()
