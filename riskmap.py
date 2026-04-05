import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backend as B
import math

def show():
    st.markdown("""
    <div style="margin-bottom:32px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 04 — PREDICTIVE RISK INTELLIGENCE</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">RISK MAP</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:10px;font-weight:300;max-width:600px;line-height:1.7;">
        Historical incident analysis drives predictive risk zone classification and resource allocation.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        hour = st.slider("Simulate time (hour)", 0, 23, 2,
                         help="Night hours (22:00–05:00) increase risk scores")
        if st.button("🔄  RECALCULATE"):
            st.rerun()

    zones = B.predict_risk_zones(hour)
    crit  = sum(1 for z in zones if z["risk_level"]=="CRITICAL")
    high  = sum(1 for z in zones if z["risk_level"]=="HIGH")

    with col2:
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Critical Zones", crit)
        k2.metric("High-Risk Zones", high)
        k3.metric("Peak Hour", "02:00–04:00 UTC")
        k4.metric("Night Boost", "+30% risk" if hour in list(range(22,24))+list(range(0,5)) else "Inactive")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Sector grid map ───────────────────────────────────────────────────────
    st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
        letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">▸ SECTOR RISK GRID — 4×3 LAYOUT</div>""",
        unsafe_allow_html=True)

    cmap = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","LOW":"#39ff14"}
    cbg  = {"CRITICAL":"rgba(255,23,68,0.15)","HIGH":"rgba(255,214,0,0.10)",
            "MEDIUM":"rgba(255,107,53,0.10)","LOW":"rgba(57,255,20,0.05)"}

    # Build 4×3 grid (12 sectors)
    zone_map = {z["sector"]: z for z in zones}
    rows_sectors = [["A1","A2","A3"],["B1","B2","B3"],["C1","C2","C3"],["D1","D2","D3"]]

    grid_html = '<div style="display:grid;grid-template-rows:repeat(4,1fr);gap:4px;">'
    for row in rows_sectors:
        grid_html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;">'
        for sec in row:
            z = zone_map.get(sec, {"sector":sec,"risk_score":0,"risk_level":"LOW"})
            c  = cmap[z["risk_level"]]
            bg = cbg[z["risk_level"]]
            pct = int(z["risk_score"] * 100)
            anim = 'animation:pulse_card 1.5s ease-in-out infinite;' if z["risk_level"]=="CRITICAL" else ''
            grid_html += f"""
            <div style="background:{bg};border:1px solid {c};padding:20px 16px;
                        text-align:center;{anim}">
              <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;
                          font-size:24px;color:{c};text-shadow:0 0 12px {c}44;">SECTOR {sec}</div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:11px;color:{c};
                          margin:6px 0;letter-spacing:1px;">{z['risk_level']}</div>
              <div style="background:rgba(255,255,255,0.05);height:3px;margin:8px 0;">
                <div style="height:3px;width:{pct}%;background:{c};"></div>
              </div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:13px;color:{c};">
                {z['risk_score']:.2f}</div>
            </div>"""
        grid_html += '</div>'
    grid_html += '</div>'

    st.markdown(f"""
    <style>
    @keyframes pulse_card {{
      0%, 100% {{ opacity:1; }}
      50% {{ opacity:0.7; }}
    }}
    </style>
    <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:20px;">
      {grid_html}
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Risk ranking table ────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">▸ RISK RANKING — ALL SECTORS</div>""",
            unsafe_allow_html=True)

        header = """<div style="display:grid;grid-template-columns:40px 80px 1fr 80px;gap:8px;
            padding:8px 16px;font-family:'Share Tech Mono',monospace;font-size:9px;
            letter-spacing:2px;color:#5d8a99;border-bottom:1px solid rgba(0,229,255,0.1);">
            <span>#</span><span>SECTOR</span><span>RISK SCORE</span><span>LEVEL</span></div>"""
        rows_html = ""
        for i, z in enumerate(zones):
            c  = cmap[z["risk_level"]]
            pct = int(z["risk_score"]*100)
            rows_html += f"""
            <div style="display:grid;grid-template-columns:40px 80px 1fr 80px;gap:8px;
                        padding:10px 16px;background:{'rgba(255,23,68,0.04)' if z['risk_level']=='CRITICAL' else 'transparent'};
                        border-left:2px solid {c};margin-bottom:1px;
                        font-family:'Share Tech Mono',monospace;font-size:11px;align-items:center;">
              <span style="color:#5d8a99;">{i+1}</span>
              <span style="color:#cce8f0;">SEC {z['sector']}</span>
              <div style="display:flex;align-items:center;gap:8px;">
                <div style="flex:1;background:rgba(255,255,255,0.05);height:4px;">
                  <div style="height:4px;width:{pct}%;background:{c};"></div>
                </div>
                <span style="color:{c};min-width:36px;">{z['risk_score']}</span>
              </div>
              <span style="color:{c};font-size:9px;border:1px solid {c};padding:2px 4px;text-align:center;">
                {z['risk_level']}</span>
            </div>"""
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:8px;">{header}{rows_html}</div>',
                    unsafe_allow_html=True)

    with col_right:
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">▸ 24-HOUR RISK FORECAST</div>""",
            unsafe_allow_html=True)

        # Simulate hourly risk for highest-risk sector
        top_sector = zones[0]["sector"]
        import random
        hourly_risk = []
        for h in range(24):
            night = h in list(range(22,24))+list(range(0,5))
            base  = B._BASE_RISK.get(top_sector, 0.5)
            r     = min(1.0, base * (1.3 if night else 1.0) + random.uniform(-0.05,0.05))
            hourly_risk.append((h, round(r, 3)))

        max_r = max(v for _,v in hourly_risk)
        bars  = ""
        for h, r in hourly_risk:
            ht  = int(r / max_r * 100)
            c   = cmap["CRITICAL"] if r > 0.8 else (cmap["HIGH"] if r > 0.6 else (cmap["MEDIUM"] if r > 0.4 else cmap["LOW"]))
            night = h in list(range(22,24))+list(range(0,5))
            bg  = "rgba(0,0,0,0.3)" if night else "transparent"
            bars += f"""<div style="flex:1;display:flex;flex-direction:column;align-items:center;
                              justify-content:flex-end;height:100px;background:{bg};" title="{h:02d}:00 — risk {r}">
              <div style="width:100%;max-width:16px;height:{ht}px;background:{c};opacity:0.85;"></div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:8px;color:#5d8a99;
                          margin-top:4px;">{h:02d}</div>
            </div>"""

        st.markdown(f"""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:20px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#00e5ff;margin-bottom:12px;">
            SECTOR {top_sector} — HIGHEST RISK
          </div>
          <div style="display:flex;align-items:flex-end;gap:1px;height:100px;">{bars}</div>
          <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:#5d8a99;margin-top:8px;">
            <span style="background:rgba(0,0,0,0.3);padding:2px 6px;">■ Night window (22:00–05:00)</span>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        # Resource recommendations
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">▸ RESOURCE RECOMMENDATIONS</div>""",
            unsafe_allow_html=True)

        recs = [
            ("SECTOR B2", "UNIT-3 + UNIT-7", "CRITICAL","Immediate dual-unit deployment"),
            ("SECTOR A1", "UNIT-9",           "HIGH",    "Single unit patrol increase"),
            ("SECTOR C3", "DRONE-2",          "HIGH",    "Aerial surveillance activation"),
            ("SECTOR B1", "UNIT-5",           "MEDIUM",  "Standby readiness elevated"),
        ]
        recs_html = ""
        for sec, unit, lvl, note in recs:
            c = cmap[lvl]
            recs_html += f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:10px 16px;border-left:3px solid {c};background:rgba(0,229,255,0.02);
                        margin-bottom:2px;font-family:'Share Tech Mono',monospace;font-size:11px;">
              <span style="color:#cce8f0;">{sec}</span>
              <span style="color:{c};">{unit}</span>
              <span style="color:#5d8a99;">{note}</span>
            </div>"""
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);">{recs_html}</div>',
                    unsafe_allow_html=True)
