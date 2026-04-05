"""
pages_src/main_dashboard.py
Master Dashboard — Live alerts, risk map, camera summary, DB reports.
"""
import streamlit as st
import sys, os, random
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.client import get_alert_stats, get_alerts, ai_threat_analysis, api_status, get_report_summary
from database.db import get_alerts_by_type, get_alerts_by_sector, get_daily_alert_counts
import backend as B

LCOLOR = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","LOW":"#39ff14","CLEAR":"#39ff14"}
LBG    = {"CRITICAL":"rgba(255,23,68,0.08)","HIGH":"rgba(255,214,0,0.06)",
          "MEDIUM":"rgba(255,107,53,0.06)","LOW":"rgba(57,255,20,0.04)"}

def show():
    st.markdown("""
    <div style="margin-bottom:24px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 00 — COMMAND CENTER</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">LIVE DASHBOARD</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:8px;font-weight:300;max-width:640px;line-height:1.7;">
        Real-time intelligence centre — database-backed alerts, AI analysis, live risk map, camera status.
      </div>
    </div>""", unsafe_allow_html=True)

    # ── API & DB status bar ───────────────────────────────────────────────────
    api = api_status()
    flask_dot = "#39ff14" if api["online"] else "#ffd600"
    st.markdown(f"""
    <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);
                padding:8px 20px;font-family:'Share Tech Mono',monospace;font-size:10px;
                display:flex;gap:28px;margin-bottom:20px;flex-wrap:wrap;">
      <span style="color:{flask_dot};">● Flask API: {'ONLINE' if api['online'] else 'LOCAL DB MODE'}</span>
      <span style="color:#39ff14;">● SQLite DB: ONLINE</span>
      <span style="color:#39ff14;">● Sensor Grid: 2,847 nodes</span>
      <span style="color:#ffd600;">● Last refresh: {datetime.now().strftime('%H:%M:%S')}</span>
    </div>""", unsafe_allow_html=True)

    # ── Live KPI row ──────────────────────────────────────────────────────────
    stats = get_alert_stats()
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Total Alerts (DB)",  stats.get("total",0))
    k2.metric("🔴 Critical",         stats.get("critical",0),  delta_color="inverse")
    k3.metric("⚠️ Unresolved",       stats.get("unresolved",0),delta_color="inverse")
    k4.metric("📅 Today",            stats.get("today",0))
    k5.metric("🧠 Model AUC",        "0.974")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Main 2-column layout ──────────────────────────────────────────────────
    left, right = st.columns([3,2])

    with left:
        # Active alert queue from DB
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:10px;">▸ ACTIVE ALERT QUEUE (DATABASE)</div>""",
            unsafe_allow_html=True)

        alerts = get_alerts(limit=10, resolved=0)
        if not alerts:
            # Seed some alerts if DB empty
            from api.client import create_alert
            sample = B.generate_alerts(8)
            for a in sample[:6]:
                create_alert(a["level"],a.get("type","sensor"),"B2",a["message"],score=a["score"])
            alerts = get_alerts(limit=10, resolved=0)

        rows_html = ""
        for a in alerts[:8]:
            c  = LCOLOR.get(a["level"],"#cce8f0")
            bg = LBG.get(a["level"],"rgba(0,0,0,0.2)")
            rows_html += f"""
            <div style="display:grid;grid-template-columns:70px 60px 1fr 70px;
                        gap:8px;padding:9px 14px;background:{bg};border-left:3px solid {c};
                        margin-bottom:2px;font-family:'Share Tech Mono',monospace;font-size:11px;">
              <span style="color:{c};font-size:9px;border:1px solid {c};padding:1px 5px;text-align:center;">{a['level']}</span>
              <span style="color:#5d8a99;">SEC {a['sector']}</span>
              <span style="color:#cce8f0;">{a['message'][:55]}</span>
              <span style="color:#5d8a99;font-size:10px;">{a.get('created_at','')[:16]}</span>
            </div>"""
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:8px;">{rows_html}</div>',
                    unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Hourly activity
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:10px;">▸ ANOMALY ACTIVITY — 48 HOURS</div>""",
            unsafe_allow_html=True)
        hourly = B.get_hourly_activity(2)
        maxv   = max(r["anomalies"] for r in hourly) or 1
        bars   = "".join(
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;'
            f'justify-content:flex-end;height:60px;" title="{r["datetime"]}: {r["anomalies"]}">'
            f'<div style="width:100%;height:{int(r["anomalies"]/maxv*55)}px;'
            f'background:{"#ff1744" if r["anomalies"]>=4 else "#ffd600" if r["anomalies"]>=2 else "#00e5ff"};'
            f'opacity:0.85;"></div></div>'
            for r in hourly[-48:])
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;">'
                    f'<div style="display:flex;gap:1px;height:60px;align-items:flex-end;">{bars}</div></div>',
                    unsafe_allow_html=True)

    with right:
        # Sector risk grid
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:10px;">▸ SECTOR RISK (LIVE)</div>""",
            unsafe_allow_html=True)
        zones = B.predict_risk_zones()
        cmap  = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","LOW":"#39ff14"}
        zm    = {z["sector"]:z for z in zones}
        grid  = ""
        for row in [["A1","A2","A3"],["B1","B2","B3"],["C1","C2","C3"],["D1","D2","D3"]]:
            grid += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:3px;margin-bottom:3px;">'
            for sec in row:
                z = zm.get(sec,{"risk_level":"LOW","risk_score":0.2})
                c = cmap[z["risk_level"]]
                grid += f'<div style="background:rgba(0,0,0,0.4);border:1px solid {c};padding:8px 4px;text-align:center;">'
                grid += f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:12px;color:{c};font-weight:bold;">{sec}</div>'
                grid += f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:9px;color:{c};">{z["risk_score"]:.2f}</div></div>'
            grid += '</div>'
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:12px;">{grid}</div>',
                    unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # AI threat summary
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:10px;">▸ AI THREAT ANALYSIS</div>""",
            unsafe_allow_html=True)
        analysis = ai_threat_analysis()
        anom_pct = analysis.get("anomaly_rate",0)*100
        st.markdown(f"""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;
                    font-family:'Share Tech Mono',monospace;font-size:11px;line-height:2.2;">
          <div>Anomaly rate: <span style="color:#ffd600;">{anom_pct:.1f}%</span></div>
          <div>Model AUC: <span style="color:#00e5ff;">{analysis.get('model_auc',0)}</span></div>
          <div>Hot sector: <span style="color:#ff1744;">SEC {analysis.get('top_risk_sector','N/A')}</span>
               <span style="color:#5d8a99;"> ({analysis.get('top_risk_score',0)})</span></div>
          <div>Active threats: <span style="color:#ff1744;">{analysis.get('active_threats',0)}</span></div>
          <div style="margin-top:8px;border-top:1px solid rgba(0,229,255,0.1);padding-top:8px;">
            {"".join(f'<div style="color:{LCOLOR.get(t["level"],chr(35)+"cce8f0")};font-size:10px;">⚠ {t["message"][:45]}</div>' for t in analysis.get("threat_summary",[]))}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── DB Report Charts ──────────────────────────────────────────────────────
    st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
        letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">▸ DATABASE REPORTS</div>""",
        unsafe_allow_html=True)

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        by_type = get_alerts_by_type()
        total   = sum(r["cnt"] for r in by_type) or 1
        clrs    = ["#ff1744","#ffd600","#ff6b35","#00e5ff","#39ff14","#b388ff"]
        bars    = "".join(
            f'<div style="margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;font-family:\'Share Tech Mono\',monospace;font-size:10px;margin-bottom:3px;">'
            f'<span style="color:#cce8f0;">{r["type"].upper()}</span>'
            f'<span style="color:{clrs[i%len(clrs)]};">{r["cnt"]}</span></div>'
            f'<div style="background:rgba(255,255,255,0.05);height:4px;">'
            f'<div style="height:4px;width:{int(r["cnt"]/total*100)}%;background:{clrs[i%len(clrs)]};"></div></div></div>'
            for i,r in enumerate(by_type)) or '<div style="color:#5d8a99;font-family:\'Share Tech Mono\',monospace;font-size:11px;">No data yet</div>'
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;">'
                    f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">ALERTS BY TYPE</div>{bars}</div>',
                    unsafe_allow_html=True)

    with col_r2:
        by_sec  = get_alerts_by_sector()
        total2  = sum(r["cnt"] for r in by_sec) or 1
        bars2   = "".join(
            f'<div style="margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;font-family:\'Share Tech Mono\',monospace;font-size:10px;margin-bottom:3px;">'
            f'<span style="color:#cce8f0;">SEC {r["sector"]}</span>'
            f'<span style="color:#00e5ff;">{r["cnt"]}</span></div>'
            f'<div style="background:rgba(255,255,255,0.05);height:4px;">'
            f'<div style="height:4px;width:{int(r["cnt"]/total2*100)}%;background:#00e5ff;opacity:0.8;"></div></div></div>'
            for r in by_sec[:6]) or '<div style="color:#5d8a99;font-family:\'Share Tech Mono\',monospace;font-size:11px;">No data yet</div>'
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;">'
                    f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">ALERTS BY SECTOR</div>{bars2}</div>',
                    unsafe_allow_html=True)

    with col_r3:
        daily  = get_daily_alert_counts(7)
        max_d  = max((r["cnt"] for r in daily), default=1)
        bars3  = "".join(
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;height:80px;">'
            f'<div style="width:100%;max-width:24px;height:{int(r["cnt"]/max_d*70)}px;background:#ff6b35;opacity:0.85;"></div>'
            f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:8px;color:#5d8a99;">{r["day"][-5:]}</div></div>'
            for r in daily) or '<div style="color:#5d8a99;font-family:\'Share Tech Mono\',monospace;font-size:11px;">No data yet</div>'
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;">'
                    f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">DAILY ALERTS (7 DAYS)</div>'
                    f'<div style="display:flex;gap:3px;height:80px;align-items:flex-end;">{bars3}</div></div>',
                    unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("🔄  REFRESH ALL DATA", use_container_width=True):
        st.rerun()
