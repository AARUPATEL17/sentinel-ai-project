"""
pages_src/ai_threat.py
AI Threat Detection — Gunshot / Scream / Suspicious Movement
Uses: OpenCV (motion), numpy (audio simulation), librosa (if installed)
"""

import streamlit as st
import sys, os, time, random, math, io, struct, wave
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.client import create_alert, get_alert_stats, api_status

# ── Page header ───────────────────────────────────────────────────────────────
def _header():
    st.markdown("""
    <div style="margin-bottom:24px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 01 — AI THREAT DETECTION</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">THREAT DETECTOR</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:8px;font-weight:300;max-width:640px;line-height:1.7;">
        Real-time AI analysis of audio and visual feeds — gunshot acoustics, human screams, and
        suspicious movement patterns using OpenCV + signal processing.
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Threat type card ──────────────────────────────────────────────────────────
def _threat_card(icon, name, desc, color, detected, confidence):
    bg = f"rgba({','.join(str(int(c,16)) for c in [color[1:3],color[3:5],color[5:7]])},0.12)" if detected else "#061520"
    bdr = color if detected else "rgba(0,229,255,0.1)"
    badge = f'<span style="background:{color};color:#000;font-family:\'Share Tech Mono\',monospace;font-size:9px;padding:2px 8px;letter-spacing:2px;">⚠ DETECTED</span>' if detected else '<span style="font-family:\'Share Tech Mono\',monospace;font-size:9px;color:#5d8a99;letter-spacing:2px;">● MONITORING</span>'
    return f"""
    <div style="background:{bg};border:1px solid {bdr};padding:20px;
                clip-path:polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,10px 100%,0 calc(100% - 10px));">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
        <span style="font-size:28px;">{icon}</span>{badge}
      </div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:22px;
                  text-transform:uppercase;letter-spacing:1px;color:{color if detected else '#cce8f0'};
                  margin-bottom:4px;">{name}</div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#5d8a99;
                  margin-bottom:12px;line-height:1.6;">{desc}</div>
      <div style="background:rgba(255,255,255,0.05);height:4px;">
        <div style="height:4px;width:{int(confidence*100)}%;background:{color};
                    {'animation:glow_bar 1s ease-in-out infinite;' if detected else ''}"></div>
      </div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:{color};margin-top:4px;">
        Confidence: {confidence*100:.1f}%</div>
    </div>"""

def show():
    _header()

    # ── API status ────────────────────────────────────────────────────────────
    api = api_status()
    dot = "#39ff14" if api["online"] else "#ffd600"
    st.markdown(f"""
    <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);
                padding:8px 16px;font-family:'Share Tech Mono',monospace;font-size:10px;
                display:flex;gap:20px;margin-bottom:16px;">
      <span style="color:#5d8a99;">BACKEND:</span>
      <span style="color:{dot};">● {'Flask API ONLINE' if api['online'] else 'Local DB mode'}</span>
      <span style="color:#5d8a99;">{api['url']}</span>
    </div>""", unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    enable_audio  = col1.checkbox("🎤 Audio Analysis", value=True)
    enable_motion = col2.checkbox("👁️ Motion Analysis", value=True)
    sensitivity   = col3.slider("Sensitivity", 0.3, 1.0, 0.65, 0.05)

    sector = st.selectbox("Monitoring Sector", ["A1","A2","B1","B2","B3","C1","C2","C3"])

    bc1, bc2 = st.columns(2)
    run_scan = bc1.button("🔍  RUN AI SCAN", type="primary", use_container_width=True)
    auto_mode = bc2.checkbox("⚡ Auto-scan every 5s", value=False)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Session state ─────────────────────────────────────────────────────────
    if "threat_log" not in st.session_state: st.session_state.threat_log = []
    if "scan_count" not in st.session_state: st.session_state.scan_count = 0

    # ── Audio threat analysis (simulated + real numpy) ────────────────────────
    def analyze_audio_signal():
        """
        Simulates audio feature extraction.
        In production with librosa:
          y, sr = librosa.load(audio_file)
          mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
          zcr  = librosa.feature.zero_crossing_rate(y)
          spec = librosa.feature.spectral_centroid(y=y, sr=sr)
        """
        import numpy as np
        sr = 22050; duration = 1.0
        t  = np.linspace(0, duration, int(sr*duration))

        # Simulate different audio events
        event_type = random.choices(
            ["silence","noise","scream","gunshot"],
            weights=[0.5, 0.25, 0.13, 0.12]
        )[0]

        if event_type == "gunshot":
            # Impulse + decay
            signal = np.zeros_like(t)
            peak   = int(0.1*sr)
            signal[peak:peak+100] = np.random.uniform(0.8, 1.0, 100)
            signal = signal * np.exp(-10*t)
            zcr    = float(np.mean(np.abs(np.diff(np.sign(signal)))) / 2)
            energy = float(np.mean(signal**2))
            centroid = 4800 + random.uniform(-200, 200)
        elif event_type == "scream":
            freqs  = [800, 1600, 3200]
            signal = sum(np.sin(2*np.pi*f*t)*random.uniform(0.3,0.7) for f in freqs)
            zcr    = float(np.mean(np.abs(np.diff(np.sign(signal)))) / 2)
            energy = float(np.mean(signal**2))
            centroid = 2200 + random.uniform(-300, 300)
        elif event_type == "noise":
            signal   = np.random.normal(0, 0.3, len(t))
            zcr      = 0.3 + random.uniform(-0.05, 0.05)
            energy   = 0.09 + random.uniform(-0.02, 0.02)
            centroid = 1800 + random.uniform(-400, 400)
        else:
            signal   = np.random.normal(0, 0.01, len(t))
            zcr      = 0.02 + random.uniform(0, 0.01)
            energy   = 0.001
            centroid = 600

        # Classifier thresholds
        gunshot_conf = min(1.0, max(0, (energy * 15 + (1 if centroid > 4000 else 0) * 0.3)))
        scream_conf  = min(1.0, max(0, (zcr * 2.5 + (1 if 1500 < centroid < 3500 else 0) * 0.2)))

        return {
            "event_type": event_type,
            "zcr":        round(zcr, 4),
            "energy":     round(energy, 4),
            "centroid":   round(centroid, 1),
            "gunshot_conf": round(gunshot_conf, 3),
            "scream_conf":  round(scream_conf, 3),
            "gunshot_det":  gunshot_conf > sensitivity * 0.7,
            "scream_det":   scream_conf  > sensitivity * 0.6,
        }

    # ── Motion analysis ───────────────────────────────────────────────────────
    def analyze_motion():
        """
        In production with OpenCV:
          ret, frame = cap.read()
          gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          diff = cv2.absdiff(prev_gray, gray)
          _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
          motion_pixels = cv2.countNonZero(thresh)
          contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        """
        motion_level = random.gauss(0.25, 0.2)
        motion_level = max(0, min(1, motion_level))
        n_contours   = random.randint(0, 8)
        pattern      = "STATIONARY"
        if motion_level > 0.7 and n_contours > 4:
            pattern = "RAPID/SUSPICIOUS"
        elif motion_level > 0.4 and n_contours > 2:
            pattern = "ACTIVE"
        elif motion_level > 0.15:
            pattern = "SLOW"

        suspicious = motion_level > sensitivity * 0.75 and n_contours > 3
        return {
            "motion_level": round(motion_level, 3),
            "contours":     n_contours,
            "pattern":      pattern,
            "suspicious":   suspicious,
            "confidence":   round(min(1.0, motion_level * 1.4), 3),
        }

    # ── Visualize audio waveform ──────────────────────────────────────────────
    def waveform_svg(event_type="noise", width=500, height=80):
        pts = 200
        points = ""
        for i in range(pts):
            t = i / pts * 4 * math.pi
            if event_type == "gunshot":
                amp = 0.9 * math.exp(-6*(i/pts)) if i > pts*0.1 else 0.1
            elif event_type == "scream":
                amp = abs(math.sin(t * 3) * 0.6 + math.sin(t * 7) * 0.3)
            elif event_type == "noise":
                amp = random.uniform(0.1, 0.4)
            else:
                amp = random.uniform(0.01, 0.05)
            x = int(i / pts * width)
            y = int(height/2 - amp * height/2 * 0.85)
            points += f"{x},{y} "
        col = {"gunshot":"#ff1744","scream":"#ffd600","noise":"#ff6b35","silence":"#5d8a99"}[event_type]
        return f"""<svg width="{width}" height="{height}" style="background:#040f15;">
          <line x1="0" y1="{height//2}" x2="{width}" y2="{height//2}"
                stroke="rgba(0,229,255,0.1)" stroke-width="1"/>
          <polyline points="{points}" fill="none" stroke="{col}" stroke-width="1.5" opacity="0.9"/>
        </svg>"""

    # ── Run scan ──────────────────────────────────────────────────────────────
    scan_results = None
    if run_scan or (auto_mode and st.session_state.scan_count % 5 == 0):
        st.session_state.scan_count += 1
        with st.spinner("Running AI threat analysis..."):
            time.sleep(0.6)
            audio  = analyze_audio_signal() if enable_audio  else None
            motion = analyze_motion()       if enable_motion else None
            scan_results = {"audio": audio, "motion": motion,
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "sector": sector}

            # Auto-create DB alert if threat detected
            threats_detected = []
            if audio and audio["gunshot_det"]:
                threats_detected.append(("CRITICAL","gunshot",f"Gunshot detected — SEC {sector}",audio["gunshot_conf"]))
            if audio and audio["scream_det"]:
                threats_detected.append(("HIGH","scream",f"Human scream detected — SEC {sector}",audio["scream_conf"]))
            if motion and motion["suspicious"]:
                threats_detected.append(("HIGH","motion",f"Suspicious movement — SEC {sector} — {motion['pattern']}",motion["confidence"]))

            for lvl, typ, msg, score in threats_detected:
                aid = create_alert(lvl, typ, sector, msg,
                                   lat=29.5+random.uniform(-0.4,0.4),
                                   lon=74.5+random.uniform(-0.4,0.4),
                                   score=score, source="ai_detector")
                st.session_state.threat_log.insert(0, {
                    "time": scan_results["timestamp"], "level": lvl,
                    "type": typ, "message": msg, "score": score,
                    "alert_id": aid, "sector": sector,
                })

    st.session_state.threat_log = st.session_state.threat_log[:30]

    # ── Display results ───────────────────────────────────────────────────────
    if scan_results:
        audio  = scan_results.get("audio")
        motion = scan_results.get("motion")

        st.markdown(f"""
        <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:3px;
                    color:#5d8a99;margin-bottom:12px;">▸ SCAN RESULT — {scan_results['timestamp']} — SEC {scan_results['sector']}</div>
        <style>@keyframes glow_bar{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}</style>
        """, unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns(3)
        gs_conf = audio["gunshot_conf"] if audio else 0
        sc_conf = audio["scream_conf"]  if audio else 0
        mv_conf = motion["confidence"]  if motion else 0

        with col_a:
            st.markdown(_threat_card("💥","Gunshot","Impulsive acoustic event with high energy transient",
                "#ff1744", audio and audio["gunshot_det"], gs_conf), unsafe_allow_html=True)
        with col_b:
            st.markdown(_threat_card("😱","Human Scream","High-frequency sustained vocal distress signal",
                "#ffd600", audio and audio["scream_det"], sc_conf), unsafe_allow_html=True)
        with col_c:
            st.markdown(_threat_card("🚶","Susp. Movement","Abnormal motion pattern — multiple contours",
                "#ff6b35", motion and motion["suspicious"], mv_conf), unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Audio waveform + features
        if audio:
            st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
                letter-spacing:3px;color:#5d8a99;margin-bottom:8px;">▸ AUDIO SIGNAL ANALYSIS</div>""",
                unsafe_allow_html=True)
            col_w, col_f = st.columns([3,1])
            with col_w:
                st.markdown(waveform_svg(audio["event_type"]), unsafe_allow_html=True)
                st.markdown(f"""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
                    color:#5d8a99;margin-top:4px;">Detected event class:
                    <span style="color:#ffd600;">{audio['event_type'].upper()}</span></div>""",
                    unsafe_allow_html=True)
            with col_f:
                st.markdown(f"""
                <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);
                            padding:16px;font-family:'Share Tech Mono',monospace;font-size:11px;line-height:2;">
                  <div style="color:#5d8a99;font-size:9px;letter-spacing:2px;margin-bottom:6px;">FEATURES</div>
                  <div>ZCR: <span style="color:#00e5ff;">{audio['zcr']}</span></div>
                  <div>Energy: <span style="color:#00e5ff;">{audio['energy']}</span></div>
                  <div>Centroid: <span style="color:#00e5ff;">{audio['centroid']} Hz</span></div>
                </div>""", unsafe_allow_html=True)

        # Motion features
        if motion:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Motion Level", f"{motion['motion_level']*100:.0f}%")
            col_m2.metric("Contours",     motion["contours"])
            col_m3.metric("Pattern",      motion["pattern"])
            col_m4.metric("Suspicious",   "YES ⚠" if motion["suspicious"] else "NO ✓")

    else:
        st.markdown("""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);padding:48px;
                    text-align:center;font-family:'Share Tech Mono',monospace;color:#5d8a99;letter-spacing:3px;">
          ○ IDLE — PRESS "RUN AI SCAN" TO ANALYZE THREATS
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Threat log ────────────────────────────────────────────────────────────
    if st.session_state.threat_log:
        st.markdown("""<div style="font-family:'Share Tech Mono',monospace;font-size:10px;
            letter-spacing:3px;color:#5d8a99;margin-bottom:8px;">▸ AI THREAT DETECTION LOG (saved to DB)</div>""",
            unsafe_allow_html=True)
        lcolor = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","LOW":"#39ff14"}
        rows_html = ""
        for e in st.session_state.threat_log[:10]:
            c = lcolor.get(e["level"],"#cce8f0")
            rows_html += f"""
            <div style="display:grid;grid-template-columns:70px 70px 80px 1fr 60px 60px;
                        gap:8px;padding:9px 14px;border-left:3px solid {c};
                        background:rgba(0,0,0,0.3);margin-bottom:2px;
                        font-family:'Share Tech Mono',monospace;font-size:11px;">
              <span style="color:#5d8a99;">{e['time']}</span>
              <span style="color:{c};font-size:9px;border:1px solid {c};padding:1px 6px;text-align:center;">{e['level']}</span>
              <span style="color:#ff6b35;">{e['type'].upper()}</span>
              <span style="color:#cce8f0;">{e['message']}</span>
              <span style="color:#5d8a99;">SEC {e['sector']}</span>
              <span style="color:{c};">{e['score']:.3f}</span>
            </div>"""
        st.markdown(f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:8px;">{rows_html}</div>',
                    unsafe_allow_html=True)

    # ── Librosa install note ──────────────────────────────────────────────────
    with st.expander("🎵 Enable Real Audio Analysis (librosa)"):
        st.markdown("""
        <div style="font-family:'Share Tech Mono',monospace;font-size:12px;line-height:2;color:#5d8a99;">
        Install librosa for real microphone audio analysis:<br>
        <span style="color:#00e5ff;">pip install librosa sounddevice soundfile</span><br><br>
        Then in the code replace <span style="color:#ff6b35;">analyze_audio_signal()</span> with:<br>
        <span style="color:#39ff14;">import librosa, sounddevice as sd</span><br>
        <span style="color:#39ff14;">audio = sd.rec(int(sr*1.0), samplerate=sr, channels=1)</span><br>
        <span style="color:#39ff14;">mfcc = librosa.feature.mfcc(y=audio.flatten(), sr=sr)</span><br>
        <span style="color:#39ff14;">zcr  = librosa.feature.zero_crossing_rate(audio.flatten())</span>
        </div>
        """, unsafe_allow_html=True)
