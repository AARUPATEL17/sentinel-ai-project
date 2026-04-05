"""
gpsmap.py — Real Interactive GPS Map with Folium
Plots real incident locations, sensor nodes, and risk zones
on an actual interactive map using Folium + streamlit-folium.
"""

import streamlit as st
import sys, os, random, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backend as B

# ── Simulated border coordinates (NW India / Pakistan border region) ───────────
BORDER_CENTER = (29.5, 74.5)
SECTOR_COORDS = {
    "A1": (31.5, 73.5), "A2": (31.5, 74.5), "A3": (31.5, 75.5),
    "B1": (30.5, 73.5), "B2": (30.5, 74.5), "B3": (30.5, 75.5),
    "C1": (29.5, 73.5), "C2": (29.5, 74.5), "C3": (29.5, 75.5),
    "D1": (28.5, 73.5), "D2": (28.5, 74.5), "D3": (28.5, 75.5),
}

def show():
    st.markdown("""
    <div style="margin-bottom:28px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 07 — GEOSPATIAL INTELLIGENCE</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">GPS MAP</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:10px;font-weight:300;max-width:620px;line-height:1.7;">
        Real interactive map — incident locations, sensor nodes, risk zones, patrol routes.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Try folium import ─────────────────────────────────────────────────────
    try:
        import folium
        from streamlit_folium import st_folium
        folium_ok = True
    except ImportError:
        folium_ok = False

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    show_incidents = col1.checkbox("📍 Incidents",    value=True)
    show_sensors   = col2.checkbox("📡 Sensor Nodes", value=True)
    show_sectors   = col3.checkbox("🗺️ Sectors",      value=True)
    show_patrol    = col4.checkbox("🚗 Patrol Route", value=True)

    col5, col6 = st.columns(2)
    map_style   = col5.selectbox("Map Style", ["OpenStreetMap","CartoDB dark_matter","CartoDB positron","Stamen Terrain"])
    n_incidents = col6.slider("Incidents to plot", 10, 100, 40)

    if st.button("🔄  REFRESH MAP"):
        st.rerun()

    if not folium_ok:
        st.warning("⚠️ Install `folium` and `streamlit-folium` for the real interactive map: `pip install folium streamlit-folium`")
        _show_fallback_map()
        return

    # ── Build Folium map ──────────────────────────────────────────────────────
    import folium
    from streamlit_folium import st_folium

    # Tile selection
    tiles_map = {
        "OpenStreetMap":      "OpenStreetMap",
        "CartoDB dark_matter":"CartoDB dark_matter",
        "CartoDB positron":   "CartoDB positron",
        "Stamen Terrain":     "Stamen Terrain",
    }
    tiles = tiles_map.get(map_style, "CartoDB dark_matter")

    m = folium.Map(
        location=BORDER_CENTER,
        zoom_start=8,
        tiles=tiles,
        attr="© OpenStreetMap contributors",
    )

    # ── Sector polygons ───────────────────────────────────────────────────────
    if show_sectors:
        zones = B.predict_risk_zones()
        zone_map = {z["sector"]: z for z in zones}
        risk_colors = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","LOW":"#39ff14"}

        for sector, (lat, lon) in SECTOR_COORDS.items():
            z    = zone_map.get(sector, {"risk_level":"LOW","risk_score":0.3})
            col  = risk_colors[z["risk_level"]]
            half = 0.45
            bounds = [[lat-half, lon-half],[lat+half, lon+half]]
            folium.Rectangle(
                bounds=bounds,
                color=col,
                weight=1.5,
                fill=True,
                fill_color=col,
                fill_opacity=0.08,
                popup=folium.Popup(f"""
                <div style="font-family:monospace;font-size:12px;min-width:140px;">
                  <b>Sector {sector}</b><br>
                  Risk Level: <b style="color:{col}">{z['risk_level']}</b><br>
                  Risk Score: {z['risk_score']}
                </div>""", max_width=180),
                tooltip=f"Sector {sector} — {z['risk_level']} ({z['risk_score']})"
            ).add_to(m)

            # Sector label
            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(
                    html=f'<div style="font-family:monospace;font-size:11px;font-weight:bold;'
                         f'color:{col};text-shadow:0 0 6px #000;white-space:nowrap;">{sector}</div>',
                    icon_size=(30, 20),
                    icon_anchor=(15, 10),
                )
            ).add_to(m)

    # ── Sensor nodes ──────────────────────────────────────────────────────────
    if show_sensors:
        sensor_group = folium.FeatureGroup(name="Sensor Nodes")
        random.seed(123)
        for sector, (lat, lon) in SECTOR_COORDS.items():
            for _ in range(random.randint(3, 7)):
                slat = lat + random.uniform(-0.4, 0.4)
                slon = lon + random.uniform(-0.4, 0.4)
                stype = random.choice(B.SENSOR_TYPES)
                val   = round(random.uniform(0.1, 0.9), 3)
                color = "#ff1744" if val > 0.75 else "#ffd600" if val > 0.5 else "#00e5ff"
                folium.CircleMarker(
                    location=[slat, slon],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.8,
                    popup=folium.Popup(f"""
                    <div style="font-family:monospace;font-size:12px;">
                      <b>Sensor Node</b><br>
                      Sector: {sector}<br>
                      Type: {stype}<br>
                      Value: {val}<br>
                      Status: {"⚠ ALERT" if val > 0.75 else "● NORMAL"}
                    </div>""", max_width=160),
                    tooltip=f"{stype} sensor — {sector}"
                ).add_to(sensor_group)
        sensor_group.add_to(m)

    # ── Incident markers ──────────────────────────────────────────────────────
    if show_incidents:
        incidents = B.generate_incidents(n_incidents)
        sev_colors = {"CRITICAL":"red","HIGH":"orange","MEDIUM":"beige","LOW":"green"}
        sev_icons  = {"CRITICAL":"exclamation-sign","HIGH":"warning-sign","MEDIUM":"info-sign","LOW":"ok-sign"}
        inc_group  = folium.FeatureGroup(name="Incidents")

        for inc in incidents:
            # Map incident to sector coordinates with jitter
            sec_lat, sec_lon = SECTOR_COORDS.get(inc["sector"], BORDER_CENTER)
            lat = sec_lat + random.uniform(-0.4, 0.4)
            lon = sec_lon + random.uniform(-0.4, 0.4)
            col = sev_colors.get(inc["severity"], "blue")
            ico = sev_icons.get(inc["severity"], "info-sign")

            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color=col, icon=ico, prefix="glyphicon"),
                popup=folium.Popup(f"""
                <div style="font-family:monospace;font-size:12px;min-width:180px;">
                  <b>{inc['incident_id']}</b><br>
                  Date: {inc['date']}<br>
                  Type: {inc['type']}<br>
                  Severity: <b>{inc['severity']}</b><br>
                  Sector: {inc['sector']}<br>
                  Outcome: {inc['outcome']}<br>
                  Duration: {inc['duration_min']} min
                </div>""", max_width=200),
                tooltip=f"{inc['type']} — {inc['severity']} — {inc['date']}"
            ).add_to(inc_group)
        inc_group.add_to(m)

    # ── Patrol route ──────────────────────────────────────────────────────────
    if show_patrol:
        patrol_points = [
            SECTOR_COORDS["A1"], SECTOR_COORDS["A2"], SECTOR_COORDS["A3"],
            SECTOR_COORDS["B3"], SECTOR_COORDS["B2"], SECTOR_COORDS["B1"],
            SECTOR_COORDS["C1"], SECTOR_COORDS["C2"], SECTOR_COORDS["C3"],
            SECTOR_COORDS["D3"], SECTOR_COORDS["D2"], SECTOR_COORDS["D1"],
        ]
        folium.PolyLine(
            patrol_points,
            color="#00e5ff",
            weight=2,
            opacity=0.6,
            dash_array="8 4",
            tooltip="Active Patrol Route — UNIT-7"
        ).add_to(m)

        # Patrol unit marker
        folium.Marker(
            location=SECTOR_COORDS["B2"],
            icon=folium.DivIcon(
                html='<div style="background:#00e5ff;color:#000;font-family:monospace;'
                     'font-size:10px;padding:3px 6px;font-weight:bold;white-space:nowrap;">🚗 UNIT-7</div>',
                icon_size=(70, 22),
                icon_anchor=(35, 11),
            ),
            tooltip="Patrol Unit 7 — Active"
        ).add_to(m)

    # ── Border line ───────────────────────────────────────────────────────────
    folium.PolyLine(
        [(32.5, 72.5),(28.0, 72.5)],
        color="#ff1744",
        weight=3,
        opacity=0.5,
        tooltip="International Border"
    ).add_to(m)

    # ── Layer control ─────────────────────────────────────────────────────────
    folium.LayerControl().add_to(m)

    # ── Render map ────────────────────────────────────────────────────────────
    map_data = st_folium(m, width=None, height=560, returned_objects=["last_clicked","last_object_clicked"])

    # ── Click info ────────────────────────────────────────────────────────────
    if map_data and map_data.get("last_clicked"):
        lc = map_data["last_clicked"]
        st.markdown(f"""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;margin-top:8px;
                    font-family:'Share Tech Mono',monospace;font-size:12px;">
          <span style="color:#5d8a99;">CLICKED COORDINATES →</span>
          <span style="color:#00e5ff;margin-left:12px;">LAT: {lc['lat']:.5f}</span>
          <span style="color:#00e5ff;margin-left:12px;">LON: {lc['lng']:.5f}</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    cols = st.columns(5)
    legends = [
        ("🔴 CRITICAL", "#ff1744", "Risk ≥ 0.80"),
        ("🟡 HIGH",     "#ffd600", "Risk ≥ 0.60"),
        ("🟠 MEDIUM",   "#ff6b35", "Risk ≥ 0.40"),
        ("🟢 LOW",      "#39ff14", "Risk < 0.40"),
        ("🔵 Sensor",   "#00e5ff", "Active node"),
    ]
    for col, (label, color, desc) in zip(cols, legends):
        col.markdown(f"""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);padding:12px;text-align:center;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:12px;color:{color};">{label}</div>
          <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:#5d8a99;margin-top:4px;">{desc}</div>
        </div>""", unsafe_allow_html=True)


def _show_fallback_map():
    """ASCII-style fallback map when folium not available."""
    zones = B.predict_risk_zones()
    zone_map = {z["sector"]: z for z in zones}
    cmap = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","LOW":"#39ff14"}

    st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
        letter-spacing:3px;color:#5d8a99;margin-bottom:12px;">▸ SECTOR MAP (TEXT MODE)</div>""", unsafe_allow_html=True)

    rows_html = ""
    for row in [["A1","A2","A3"],["B1","B2","B3"],["C1","C2","C3"],["D1","D2","D3"]]:
        rows_html += '<div style="display:flex;gap:4px;margin-bottom:4px;">'
        for sec in row:
            z = zone_map.get(sec, {"risk_level":"LOW","risk_score":0.3})
            c = cmap[z["risk_level"]]
            rows_html += f"""<div style="flex:1;background:rgba(0,0,0,0.4);border:1px solid {c};
                padding:20px;text-align:center;font-family:'Share Tech Mono',monospace;">
              <div style="color:{c};font-size:16px;font-weight:bold;">{sec}</div>
              <div style="color:{c};font-size:10px;margin-top:4px;">{z['risk_score']}</div>
            </div>"""
        rows_html += '</div>'

    st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:16px;">{rows_html}</div>',
                unsafe_allow_html=True)
