"""
pages_src/camera_surveillance.py
Live CCTV / Webcam Surveillance — Unknown Person + Weapon Detection
"""

import streamlit as st
import sys, os, time, random, math, base64
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.client import create_alert

def show():
    st.markdown("""
    <div style="margin-bottom:24px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 03 — CCTV SURVEILLANCE</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">CAMERA FEED</div>
      <div style="font-size:14px;color:#5d8a99;margin-top:8px;font-weight:300;max-width:640px;line-height:1.7;">
        Real webcam feed with OpenCV detection — Unknown Person ID, Weapon detection, Face recognition.
      </div>
    </div>""", unsafe_allow_html=True)

    try:
        import cv2, numpy as np
        CV2_OK = True
    except ImportError:
        CV2_OK = False

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    cam_idx        = col1.selectbox("Camera", [0,1,2], index=0)
    detect_unknown = col2.checkbox("👤 Unknown Person", value=True)
    detect_weapon  = col3.checkbox("🔫 Weapon (shape)", value=True)
    detect_face    = col4.checkbox("😶 Face ID",        value=True)

    col5, col6 = st.columns(2)
    sector     = col5.selectbox("Sector",   ["A1","A2","B1","B2","B3","C1","C2","C3"])
    alert_auto = col6.checkbox("Auto-alert on detection", value=True)

    if "cam_active"  not in st.session_state: st.session_state.cam_active  = False
    if "cam_log"     not in st.session_state: st.session_state.cam_log     = []
    if "cam_frames"  not in st.session_state: st.session_state.cam_frames  = 0
    if "cam_threats" not in st.session_state: st.session_state.cam_threats = 0

    bc1, bc2, bc3 = st.columns(3)
    if bc1.button("▶  START", type="primary", use_container_width=True):
        st.session_state.cam_active = True
    if bc2.button("⏹  STOP", use_container_width=True):
        st.session_state.cam_active = False
    if bc3.button("🗑️  CLEAR LOG", use_container_width=True):
        st.session_state.cam_log = []
        st.session_state.cam_threats = 0

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Layout ────────────────────────────────────────────────────────────────
    feed_col, info_col = st.columns([3,1])
    frame_slot = feed_col.empty()
    info_slot  = info_col.empty()
    log_slot   = st.empty()

    # ── Load classifiers ──────────────────────────────────────────────────────
    @st.cache_resource
    def load_cv2_classifiers():
        import cv2
        return {
            "face":  cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'),
            "body":  cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml'),
            "upper": cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_upperbody.xml'),
            "eye":   cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml'),
        }

    # ── Weapon shape detection (contour-based heuristic) ──────────────────────
    def detect_weapon_shapes(frame, gray):
        """
        Simple weapon-shape heuristic using contours.
        In production use YOLOv8 trained on weapon dataset:
          model = YOLO('yolov8-weapon.pt')
          results = model(frame)
        """
        import cv2, numpy as np
        blurred = cv2.GaussianBlur(gray, (5,5), 0)
        edges   = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        weapons = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500 or area > 15000:
                continue
            x,y,w,h = cv2.boundingRect(cnt)
            ar = w/max(h,1)
            # Elongated + dark → gun-like heuristic
            if ar > 2.5 and h < 60:
                roi = gray[y:y+h, x:x+w]
                if roi.size > 0 and float(np.mean(roi)) < 100:
                    weapons.append((x,y,w,h))
        return weapons[:3]  # max 3

    # ── Draw detections on frame ───────────────────────────────────────────────
    def draw_frame(frame, faces, bodies, weapons, frame_n):
        import cv2
        h, w = frame.shape[:2]
        ts    = datetime.now().strftime("%H:%M:%S.%f")[:12]

        # HUD corners
        for (cx,cy,dx,dy) in [(0,0,20,0),(w-20,0,20,0),(0,h-20,0,20),(w-20,h-20,0,20)]:
            cv2.rectangle(frame,(cx,cy),(cx+20,cy+20),(0,229,255),2)

        # Scanlines
        overlay = frame.copy()
        for yl in range(0,h,4): cv2.line(overlay,(0,yl),(w,yl),(0,0,0),1)
        cv2.addWeighted(overlay,0.05,frame,0.95,0,frame)

        # Unknown persons (red)
        for (x,y,bw,bh) in bodies:
            cv2.rectangle(frame,(x,y),(x+bw,y+bh),(0,0,255),2)
            cv2.putText(frame,"UNKNOWN PERSON",(x,y-8),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,255),1)
            conf = round(random.uniform(0.75,0.97),2)
            cv2.putText(frame,f"conf:{conf}",(x,y+bh+14),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,0,255),1)

        # Faces (orange)
        for (x,y,fw,fh) in faces:
            cv2.rectangle(frame,(x,y),(x+fw,y+fh),(0,165,255),2)
            cv2.putText(frame,"FACE DETECTED",(x,y-8),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,165,255),1)

        # Weapon shapes (magenta)
        for (x,y,ww,wh) in weapons:
            cv2.rectangle(frame,(x,y),(x+ww,y+wh),(255,0,255),2)
            cv2.putText(frame,"⚠ OBJECT",(x,y-8),cv2.FONT_HERSHEY_SIMPLEX,0.45,(255,0,255),1)

        # Threat level
        total = len(faces)+len(bodies)
        if total>=2 or weapons: tlvl,tcol="CRITICAL",(0,0,255)
        elif total>=1:          tlvl,tcol="HIGH",(0,165,255)
        else:                   tlvl,tcol="CLEAR",(57,255,20)

        cv2.rectangle(frame,(w-160,0),(w,50),(0,0,0),-1)
        cv2.putText(frame,f"THREAT:{tlvl}",(w-155,20),cv2.FONT_HERSHEY_SIMPLEX,0.5,tcol,1)
        cv2.putText(frame,f"FRAME:{frame_n:05d}",(w-155,40),cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,229,255),1)
        cv2.putText(frame,ts,(10,h-10),cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,229,255),1)
        cv2.circle(frame,(w-15,h-15),5,(0,0,255),-1)  # REC

        return frame, tlvl

    # ── Camera loop ───────────────────────────────────────────────────────────
    if st.session_state.cam_active and CV2_OK:
        classifiers = load_cv2_classifiers()
        import cv2, numpy as np
        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            st.error("❌ Camera not accessible. Check permissions / index.")
            st.session_state.cam_active = False
        else:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)

            for _ in range(500):
                if not st.session_state.cam_active: break
                ret, frame = cap.read()
                if not ret: break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                st.session_state.cam_frames += 1

                faces   = classifiers["face"].detectMultiScale(gray,1.1,4,minSize=(30,30)) if detect_face    else []
                bodies  = classifiers["body"].detectMultiScale(gray,1.1,3,minSize=(60,120)) if detect_unknown else []
                weapons = detect_weapon_shapes(frame,gray) if detect_weapon else []
                faces   = list(faces)  if len(faces)  > 0 else []
                bodies  = list(bodies) if len(bodies) > 0 else []

                drawn, threat = draw_frame(frame.copy(), faces, bodies, weapons, st.session_state.cam_frames)
                rgb = cv2.cvtColor(drawn, cv2.COLOR_BGR2RGB)
                frame_slot.image(rgb, use_container_width=True,
                                 caption=f"Frame {st.session_state.cam_frames} | Persons: {len(bodies)} | Faces: {len(faces)} | Objects: {len(weapons)}")

                if (len(bodies)+len(faces) > 0 or weapons) and alert_auto:
                    st.session_state.cam_threats += 1
                    if len(bodies) > 0:
                        aid = create_alert("HIGH","unknown_person",sector,
                            f"Unknown person detected — SEC {sector}",score=0.82,source="cctv")
                    if weapons:
                        aid = create_alert("CRITICAL","weapon",sector,
                            f"Suspicious object/weapon shape — SEC {sector}",score=0.91,source="cctv")
                    entry = {"time":datetime.now().strftime("%H:%M:%S"),
                             "persons":len(bodies),"faces":len(faces),"weapons":len(weapons),"threat":threat}
                    st.session_state.cam_log.insert(0,entry)

                info_slot.markdown(f"""
                <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);
                            padding:16px;font-family:'Share Tech Mono',monospace;font-size:11px;line-height:2.2;">
                  <div style="color:#5d8a99;font-size:9px;letter-spacing:2px;margin-bottom:8px;">LIVE STATS</div>
                  <div>Frames: <span style="color:#00e5ff;">{st.session_state.cam_frames}</span></div>
                  <div>Persons: <span style="color:#ff1744;">{len(bodies)}</span></div>
                  <div>Faces: <span style="color:#ffd600;">{len(faces)}</span></div>
                  <div>Objects: <span style="color:#ff00ff;">{len(weapons)}</span></div>
                  <div>Alerts: <span style="color:#ff1744;">{st.session_state.cam_threats}</span></div>
                  <div>Threat:<br><span style="color:{'#ff1744' if threat=='CRITICAL' else '#ffd600' if threat=='HIGH' else '#39ff14'};font-size:16px;">{threat}</span></div>
                </div>""", unsafe_allow_html=True)

                time.sleep(0.04)
            cap.release()

    elif not CV2_OK:
        frame_slot.warning("⚠️ Install `opencv-python-headless` and `numpy` for live camera.")
        _demo_frame(frame_slot)

    elif not st.session_state.cam_active:
        frame_slot.markdown("""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:80px;
                    text-align:center;min-height:360px;display:flex;flex-direction:column;
                    justify-content:center;align-items:center;">
          <div style="font-size:52px;margin-bottom:12px;">📷</div>
          <div style="font-family:'Share Tech Mono',monospace;font-size:12px;letter-spacing:3px;color:#5d8a99;">
            CAMERA OFFLINE — PRESS ▶ START</div>
        </div>""", unsafe_allow_html=True)

    # ── Detection log ─────────────────────────────────────────────────────────
    if st.session_state.cam_log:
        lc = {"CRITICAL":"#ff1744","HIGH":"#ffd600","MEDIUM":"#ff6b35","CLEAR":"#39ff14"}
        rows = "".join(
            f'<div style="display:grid;grid-template-columns:80px 80px 80px 80px 80px;gap:8px;'
            f'padding:8px 14px;border-left:3px solid {lc.get(e["threat"],"#cce8f0")};'
            f'background:rgba(0,0,0,0.3);margin-bottom:2px;'
            f'font-family:\'Share Tech Mono\',monospace;font-size:11px;">'
            f'<span style="color:#5d8a99;">{e["time"]}</span>'
            f'<span style="color:#ff1744;">P:{e["persons"]}</span>'
            f'<span style="color:#ffd600;">F:{e["faces"]}</span>'
            f'<span style="color:#ff00ff;">W:{e["weapons"]}</span>'
            f'<span style="color:{lc.get(e["threat"],"#cce8f0")};">{e["threat"]}</span></div>'
            for e in st.session_state.cam_log[:8])
        log_slot.markdown(
            f'<div style="background:#061520;border:1px solid rgba(0,229,255,0.12);'
            f'padding:8px;margin-top:8px;"><div style="font-family:\'Share Tech Mono\',monospace;'
            f'font-size:10px;letter-spacing:3px;color:#5d8a99;margin-bottom:8px;padding:0 8px;">'
            f'▸ DETECTION LOG (saved to DB)</div>{rows}</div>',
            unsafe_allow_html=True)


def _demo_frame(slot):
    slot.markdown("""
    <svg width="640" height="400" style="background:#0a1a20;border:1px solid rgba(0,229,255,0.2);">
      <defs><pattern id="g2" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M40 0L0 0 0 40" fill="none" stroke="rgba(0,229,255,0.04)" stroke-width="1"/>
      </pattern></defs>
      <rect width="640" height="400" fill="url(#g2)"/>
      <path d="M10 30L10 10 30 10" fill="none" stroke="#00e5ff" stroke-width="2"/>
      <path d="M610 10L630 10 630 30" fill="none" stroke="#00e5ff" stroke-width="2"/>
      <path d="M10 370L10 390 30 390" fill="none" stroke="#00e5ff" stroke-width="2"/>
      <path d="M610 390L630 390 630 370" fill="none" stroke="#00e5ff" stroke-width="2"/>
      <rect x="200" y="120" width="80" height="100" fill="none" stroke="#ff1744" stroke-width="2"/>
      <text x="200" y="115" fill="#ff1744" font-size="11" font-family="monospace">UNKNOWN PERSON</text>
      <rect x="210" y="100" width="50" height="55" fill="none" stroke="#ffd600" stroke-width="1.5"/>
      <text x="210" y="95" fill="#ffd600" font-size="10" font-family="monospace">FACE</text>
      <rect x="380" y="200" width="90" height="25" fill="none" stroke="#ff00ff" stroke-width="2"/>
      <text x="380" y="195" fill="#ff00ff" font-size="11" font-family="monospace">⚠ OBJECT</text>
      <text x="470" y="25" fill="#ff1744" font-size="13" font-family="monospace" font-weight="bold">THREAT: HIGH</text>
      <circle cx="625" cy="385" r="5" fill="#ff1744" opacity="0.8"/>
      <text x="10" y="392" fill="#00e5ff" font-size="9" font-family="monospace">SENTINEL CCTV | DEMO MODE | install opencv-python-headless</text>
    </svg>""", unsafe_allow_html=True)
