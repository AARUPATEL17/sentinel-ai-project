"""
realtime.py — Real-Time Sensor Simulation with Live Updating
Auto-refreshes every N seconds, shows live sensor feed,
rolling anomaly rate, and live alert generation.
"""

import streamlit as st
import sys, os, time, random, math
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backend as B

def show():
    st.markdown("""
    <div style="margin-bottom:28px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 08 — LIVE TELEMETRY</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">REAL-TIME FEED</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:10px;font-weight:300;max-width:620px;line-height:1.7;">
        Live sensor telemetry with auto-refresh, rolling anomaly tracking, and instant alerts.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Session state ─────────────────────────────────────────────────────────
    if "rt_running"       not in st.session_state: st.session_state.rt_running       = False
    if "rt_readings"      not in st.session_state: st.session_state.rt_readings      = []
    if "rt_anomaly_rates" not in st.session_state: st.session_state.rt_anomaly_rates = []
    if "rt_alerts"        not in st.session_state: st.session_state.rt_alerts        = []
    if "rt_tick"          not in st.session_state: st.session_state.rt_tick          = 0
    if "rt_total_anom"    not in st.session_state: st.session_state.rt_total_anom    = 0
    if "rt_total_reads"   not in st.session_state: st.session_state.rt_total_reads   = 0

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    refresh_rate  = col1.slider("Refresh interval (sec)", 1, 10, 2)
    sensors_per_tick = col2.slider("Readings per tick", 5, 50, 15)
    anomaly_prob  = col3.slider("Anomaly probability", 0.01, 0.30, 0.08, 0.01,
                                help="Simulate different threat environments")

    bc1, bc2, bc3 = st.columns(3)
    if bc1.button("▶  START SIMULATION", type="primary"):
        st.session_state.rt_running = True
    if bc2.button("⏹  STOP"):
        st.session_state.rt_running = False
    if bc3.button("🗑️  RESET ALL"):
        st.session_state.rt_readings      = []
        st.session_state.rt_anomaly_rates = []
        st.session_state.rt_alerts        = []
        st.session_state.rt_tick          = 0
        st.session_state.rt_total_anom    = 0
        st.session_state.rt_total_reads   = 0
        st.session_state.rt_running       = False
        st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Status badge ──────────────────────────────────────────────────────────
    status_color = "#39ff14" if st.session_state.rt_running else "#5d8a99"
    status_text  = "● LIVE" if st.session_state.rt_running else "○ OFFLINE"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:20px;background:#061520;
                border:1px solid rgba(0,229,255,0.12);padding:12px 20px;margin-bottom:16px;">
      <span style="font-family:'Share Tech Mono',monospace;font-size:13px;color:{status_color};
                   letter-spacing:3px;">{status_text}</span>
      <span style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#5d8a99;">
        TICK #{st.session_state.rt_tick:04d}</span>
      <span style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#5d8a99;">
        TOTAL READS: {st.session_state.rt_total_reads}</span>
      <span style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#ff1744;">
        ANOMALIES: {st.session_state.rt_total_anom}</span>
      <span style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#ffd600;">
        ANOM RATE: {st.session_state.rt_total_anom/max(st.session_state.rt_total_reads,1)*100:.1f}%</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Placeholder slots ─────────────────────────────────────────────────────
    kpi_slot    = st.empty()
    chart_slot  = st.empty()
    feed_slot   = st.empty()
    alert_slot  = st.empty()

    def render_kpis():
        reads = st.session_state.rt_readings
        if not reads:
            return
        last10  = reads[-10:]
        avg_val = sum(r["value"] for r in last10) / len(last10)
        anom_10 = sum(1 for r in last10 if r["anomaly"])
        active_sectors = len(set(r["sector"] for r in reads[-50:]))

        kpi_slot.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px;">
          <div style="background:#061520;border:1px solid rgba(0,229,255,0.15);padding:16px;text-align:center;
                      clip-path:polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,8px 100%,0 calc(100% - 8px));">
            <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:36px;color:#00e5ff;">
              {st.session_state.rt_tick}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;">TICKS</div>
          </div>
          <div style="background:#061520;border:1px solid rgba(255,23,68,0.2);padding:16px;text-align:center;
                      clip-path:polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,8px 100%,0 calc(100% - 8px));">
            <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:36px;color:#ff1744;">
              {anom_10}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;">ANOMALIES (LAST 10)</div>
          </div>
          <div style="background:#061520;border:1px solid rgba(0,229,255,0.15);padding:16px;text-align:center;
                      clip-path:polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,8px 100%,0 calc(100% - 8px));">
            <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:36px;color:#ffd600;">
              {avg_val:.3f}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;">AVG SENSOR VALUE</div>
          </div>
          <div style="background:#061520;border:1px solid rgba(57,255,20,0.15);padding:16px;text-align:center;
                      clip-path:polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,8px 100%,0 calc(100% - 8px));">
            <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:36px;color:#39ff14;">
              {active_sectors}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:3px;color:#5d8a99;">ACTIVE SECTORS</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    def render_chart():
        rates = st.session_state.rt_anomaly_rates[-40:]
        if len(rates) < 2: return
        max_r = max(rates) or 1
        bars  = ""
        for r in rates:
            h = int(r / max_r * 80)
            c = "#ff1744" if r > 0.15 else "#ffd600" if r > 0.08 else "#00e5ff"
            bars += f'<div style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:80px;">'
            bars += f'<div style="width:100%;height:{h}px;background:{c};opacity:0.85;"></div></div>'

        chart_slot.markdown(f"""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;margin-bottom:12px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:3px;
                      color:#5d8a99;margin-bottom:8px;">▸ ROLLING ANOMALY RATE — LAST 40 TICKS</div>
          <div style="display:flex;align-items:flex-end;gap:1px;height:80px;">{bars}</div>
          <div style="display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;
                      font-size:9px;color:#5d8a99;margin-top:4px;">
            <span>40 ticks ago</span>
            <span style="color:#ff1744;">■ HIGH (&gt;15%)</span>
            <span style="color:#ffd600;">■ MED (&gt;8%)</span>
            <span style="color:#00e5ff;">■ LOW</span>
            <span>NOW</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    def render_feed():
        reads = st.session_state.rt_readings
        if not reads: return
        last = list(reversed(reads[-15:]))
        rows = ""
        for r in last:
            c = "#ff1744" if r["anomaly"] else "#00e5ff"
            flag = "⚠ ANOM" if r["anomaly"] else "·  OK "
            rows += f"""
            <div style="display:grid;grid-template-columns:80px 60px 80px 70px 70px 60px;
                        gap:8px;padding:7px 14px;border-left:2px solid {c};
                        background:{"rgba(255,23,68,0.05)" if r["anomaly"] else "rgba(0,0,0,0.2)"};
                        margin-bottom:1px;font-family:'Share Tech Mono',monospace;font-size:10px;
                        animation:fadeIn 0.3s ease;">
              <span style="color:#5d8a99;">{r['timestamp']}</span>
              <span style="color:#cce8f0;">SEC {r['sector']}</span>
              <span style="color:#5d8a99;">{r['sensor_type']}</span>
              <span style="color:#cce8f0;">Val: {r['value']}</span>
              <span style="color:#5d8a99;">Conf: {r['confidence']}</span>
              <span style="color:{c};">{flag}</span>
            </div>"""

        feed_slot.markdown(f"""
        <style>@keyframes fadeIn {{from{{opacity:0;transform:translateY(-4px)}}to{{opacity:1;transform:none}}}}</style>
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:12px;margin-bottom:12px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:3px;
                      color:#5d8a99;margin-bottom:8px;">▸ LIVE SENSOR STREAM</div>
          <div style="display:grid;grid-template-columns:80px 60px 80px 70px 70px 60px;
                      gap:8px;padding:6px 14px;border-bottom:1px solid rgba(0,229,255,0.1);
                      font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:2px;color:#5d8a99;margin-bottom:4px;">
            <span>TIME</span><span>SECTOR</span><span>TYPE</span><span>VALUE</span><span>CONF</span><span>STATUS</span>
          </div>
          {rows}
        </div>
        """, unsafe_allow_html=True)

    def render_alerts():
        alerts = st.session_state.rt_alerts[-5:]
        if not alerts: return
        lcolor = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35"}
        rows = ""
        for a in reversed(alerts):
            c = lcolor.get(a["level"],"#cce8f0")
            rows += f"""
            <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
                        border-left:3px solid {c};background:rgba(0,0,0,0.3);
                        margin-bottom:2px;font-family:'Share Tech Mono',monospace;font-size:11px;">
              <span style="color:{c};font-size:9px;border:1px solid {c};padding:2px 7px;">{a['level']}</span>
              <span style="color:#5d8a99;">{a['time']}</span>
              <span style="color:#cce8f0;flex:1;">{a['message']}</span>
              <span style="color:{c};">Score: {a['score']}</span>
            </div>"""

        alert_slot.markdown(f"""
        <div style="background:#061520;border:1px solid rgba(255,23,68,0.2);padding:12px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:3px;
                      color:#5d8a99;margin-bottom:8px;">▸ REAL-TIME ALERT FEED</div>
          {rows}
        </div>
        """, unsafe_allow_html=True)

    # ── Simulation loop ───────────────────────────────────────────────────────
    if st.session_state.rt_running:
        for _ in range(200):
            if not st.session_state.rt_running:
                break

            # Generate new sensor readings for this tick
            tick_rows = []
            now_str   = datetime.now().strftime("%H:%M:%S")
            for _ in range(sensors_per_tick):
                sector = random.choice(B.SECTORS)
                stype  = random.choice(B.SENSOR_TYPES)
                is_anom = random.random() < anomaly_prob
                value   = round(random.uniform(0.7, 1.0) if is_anom else max(0, min(1, random.gauss(0.3, 0.15))), 4)
                tick_rows.append({
                    "timestamp":   now_str,
                    "sector":      sector,
                    "sensor_type": stype,
                    "value":       value,
                    "anomaly":     is_anom,
                    "confidence":  round(random.uniform(0.82, 0.99) if is_anom else random.uniform(0.5, 0.78), 3),
                })

            st.session_state.rt_readings.extend(tick_rows)
            st.session_state.rt_readings = st.session_state.rt_readings[-300:]
            st.session_state.rt_tick    += 1
            st.session_state.rt_total_reads += len(tick_rows)

            tick_anoms = sum(1 for r in tick_rows if r["anomaly"])
            st.session_state.rt_total_anom += tick_anoms
            rate = tick_anoms / len(tick_rows)
            st.session_state.rt_anomaly_rates.append(round(rate, 4))
            st.session_state.rt_anomaly_rates = st.session_state.rt_anomaly_rates[-200:]

            # Generate real-time alerts from anomalies
            for r in tick_rows:
                if r["anomaly"] and r["value"] > 0.75:
                    score  = round(r["value"] * r["confidence"], 3)
                    level  = "CRITICAL" if score > 0.85 else "HIGH" if score > 0.70 else "MEDIUM"
                    msgs   = {
                        "CRITICAL": f"High-value anomaly — SEC {r['sector']} — {r['sensor_type']}",
                        "HIGH":     f"Anomaly detected — SEC {r['sector']} — {r['sensor_type']}",
                        "MEDIUM":   f"Elevated reading — SEC {r['sector']} — val {r['value']}",
                    }
                    st.session_state.rt_alerts.append({
                        "level": level, "time": now_str,
                        "message": msgs[level], "score": score,
                    })
            st.session_state.rt_alerts = st.session_state.rt_alerts[-30:]

            render_kpis()
            render_chart()
            render_feed()
            render_alerts()

            time.sleep(refresh_rate)
    else:
        render_kpis()
        render_chart()
        render_feed()
        render_alerts()
        if not st.session_state.rt_readings:
            kpi_slot.markdown("""
            <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);padding:40px;text-align:center;
                        font-family:'Share Tech Mono',monospace;color:#5d8a99;letter-spacing:3px;">
              ○ SIMULATION OFFLINE — PRESS ▶ START TO BEGIN
            </div>""", unsafe_allow_html=True)
