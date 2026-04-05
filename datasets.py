import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backend as B
import pandas as pd

def show():
    st.markdown("""
    <div style="margin-bottom:32px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 05 — DATA REPOSITORY</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">DATASETS</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:10px;font-weight:300;max-width:600px;line-height:1.7;">
        Generate, preview and download simulated border surveillance datasets for model training.
      </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["📡  SENSOR DATA", "📋  INCIDENTS", "⚠️  ALERTS", "ℹ️  OPEN SOURCES"])

    # ── Sensor data ───────────────────────────────────────────────────────────
    with tabs[0]:
        col1, col2 = st.columns([1, 3])
        with col1:
            n = st.slider("Records", 100, 2000, 500, 100)
            seed = st.number_input("Random seed", 0, 9999, 42)
            gen = st.button("⚙️  GENERATE DATASET")

        rows = B.generate_sensor_readings(n, seed=int(seed))
        df   = pd.DataFrame(rows)
        stats = B.get_sensor_stats(rows)

        with col2:
            k1,k2,k3,k4 = st.columns(4)
            k1.metric("Records",        f"{stats['total']:,}")
            k2.metric("Anomalies",      stats["anomaly_count"])
            k3.metric("Anomaly Rate",   f"{stats['anomaly_rate']}%")
            k4.metric("Sensors Covered", len(B.SENSOR_TYPES))

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.dataframe(df.head(100), use_container_width=True, height=350)
        csv = df.to_csv(index=False)
        st.download_button("⬇ DOWNLOAD SENSOR CSV", csv, "sentinel_sensor_data.csv", "text/csv", use_container_width=True)

    # ── Incidents ─────────────────────────────────────────────────────────────
    with tabs[1]:
        n_inc = st.slider("Incident records", 50, 500, 200, 50)
        incidents = B.generate_incidents(n_inc)
        df_inc = pd.DataFrame(incidents)

        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Total Incidents", len(incidents))
        k2.metric("Unique Sectors",  df_inc["sector"].nunique())
        k3.metric("Incident Types",  df_inc["type"].nunique())
        k4.metric("Date Span",       "3 Years")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.dataframe(df_inc.head(100), use_container_width=True, height=350)
        csv2 = df_inc.to_csv(index=False)
        st.download_button("⬇ DOWNLOAD INCIDENTS CSV", csv2, "sentinel_incidents.csv", "text/csv", use_container_width=True)

    # ── Alerts ────────────────────────────────────────────────────────────────
    with tabs[2]:
        n_al = st.slider("Alert records", 20, 200, 50, 10)
        alerts = B.generate_alerts(n_al)
        df_al  = pd.DataFrame(alerts)

        k1,k2,k3 = st.columns(3)
        k1.metric("Total Alerts",     len(alerts))
        k2.metric("Suppressed",       sum(1 for a in alerts if a["suppressed"]))
        k3.metric("Avg Threat Score", round(sum(a["score"] for a in alerts)/len(alerts),3))

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.dataframe(df_al, use_container_width=True, height=350)
        csv3 = df_al.to_csv(index=False)
        st.download_button("⬇ DOWNLOAD ALERTS CSV", csv3, "sentinel_alerts.csv", "text/csv", use_container_width=True)

    # ── Open sources ──────────────────────────────────────────────────────────
    with tabs[3]:
        sources = [
            ("🛰️ Sentinel-2 Satellite", "ESA Copernicus", "Multispectral satellite imagery at 10m resolution. Ideal for land-cover change detection and border region mapping.",
             ["Remote Sensing","Multi-spectral","Open","GeoTIFF"], "https://scihub.copernicus.eu"),
            ("🌍 Landsat-8 Imagery", "NASA / USGS", "30m resolution surface reflectance data. Historical archive back to 1972 useful for long-term change analysis.",
             ["Historical","Thermal","Open","Cloud"], "https://earthexplorer.usgs.gov"),
            ("🎯 VisDrone Dataset", "AISKYEYE Lab", "Drone-captured object detection dataset with 10 classes including pedestrians, vehicles, and more.",
             ["Object Detection","YOLO","Annotated","Drone"], "https://github.com/VisDrone/VisDrone-Dataset"),
            ("🤖 COCO Dataset", "Microsoft", "Large-scale object detection, segmentation, and captioning. Commonly used for transfer learning in surveillance tasks.",
             ["Detection","Segmentation","80 classes","Benchmark"], "https://cocodataset.org"),
            ("📊 UCR Time Series", "UC Riverside", "Extensive archive of labeled time-series datasets for anomaly detection and classification tasks.",
             ["Time Series","Anomaly","Labeled","CSV"], "https://www.cs.ucr.edu/~eamonn/time_series_data_2018"),
            ("🌐 OpenStreetMap", "OSM Contributors", "Detailed geographic data including roads, borders, checkpoints, and terrain features for spatial risk modeling.",
             ["Geospatial","Vector","Real-time","Open"], "https://www.openstreetmap.org"),
        ]

        for i in range(0, len(sources), 2):
            c1, c2 = st.columns(2)
            for col, (title, org, desc, tags, url) in zip([c1,c2], sources[i:i+2]):
                tags_html = " ".join(f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:9px;letter-spacing:2px;padding:2px 8px;border:1px solid rgba(0,229,255,0.2);color:#5d8a99;">{t}</span>' for t in tags)
                col.markdown(f"""
                <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:24px;margin-bottom:16px;height:200px;">
                  <div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:20px;
                              color:#cce8f0;text-transform:uppercase;margin-bottom:4px;">{title}</div>
                  <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:2px;
                              color:#ff6b35;margin-bottom:10px;">{org.upper()}</div>
                  <div style="font-size:13px;color:#5d8a99;line-height:1.6;margin-bottom:12px;">{desc}</div>
                  <div style="display:flex;flex-wrap:wrap;gap:6px;">{tags_html}</div>
                </div>""", unsafe_allow_html=True)
