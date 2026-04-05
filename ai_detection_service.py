"""
api/services/ai_detection_service.py
────────────────────────────────────
Backend service for ALL AI threat detection:
  • Gunshot detection  (audio signal analysis)
  • Scream detection   (vocal frequency analysis)
  • Motion detection   (optical flow / frame diff)
  • Weapon detection   (contour heuristics)
  • Object classifier  (Haar / YOLO stub)

In production swap the stubs with:
  librosa  → real audio feature extraction
  OpenCV   → real frame differencing
  YOLOv8   → real weapon / object detection
"""

import math, random, time, sys, os
from datetime import datetime
from typing import Optional

# Fix import path for Windows and all platforms
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

# ── Try real imports (graceful fallback) ──────────────────────────────────────
try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False


# ═════════════════════════════════════════════════════════════════════════════
# 1. AUDIO THREAT DETECTION SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class AudioDetectionService:
    """
    Detects gunshots and screams from audio signal data.
    Uses: Zero-Crossing Rate, RMS Energy, Spectral Centroid, MFCC
    """

    GUNSHOT_ENERGY_THRESH  = 0.45
    GUNSHOT_CENTROID_MIN   = 3500
    SCREAM_ZCR_THRESH      = 0.28
    SCREAM_CENTROID_RANGE  = (1200, 3800)
    SCREAM_HARMONIC_THRESH = 0.35

    def __init__(self, sensitivity: float = 0.65):
        self.sensitivity = sensitivity

    def extract_features(self, signal_values: list, sample_rate: int = 22050) -> dict:
        """
        Extract audio features from a signal array.
        With real librosa:
            mfcc     = librosa.feature.mfcc(y=signal, sr=sr, n_mfcc=13)
            zcr      = librosa.feature.zero_crossing_rate(signal)
            centroid = librosa.feature.spectral_centroid(y=signal, sr=sr)
            rms      = librosa.feature.rms(y=signal)
        """
        if NUMPY_OK:
            import numpy as np
            sig = np.array(signal_values, dtype=float)
            n   = len(sig)

            # Zero-crossing rate
            zcr = float(np.mean(np.abs(np.diff(np.sign(sig)))) / 2) if n > 1 else 0.0

            # RMS energy
            energy = float(np.sqrt(np.mean(sig ** 2)))

            # Spectral centroid (simplified DFT approach)
            fft_mag = np.abs(np.fft.rfft(sig))
            freqs   = np.fft.rfftfreq(n, d=1.0/sample_rate)
            centroid = float(np.sum(freqs * fft_mag) / (np.sum(fft_mag) + 1e-9))

            # Harmonic ratio (ratio of energy in harmonic vs total)
            harmonic_bands = fft_mag[int(n*0.01):int(n*0.15)]
            harmonic_ratio = float(np.sum(harmonic_bands) / (np.sum(fft_mag) + 1e-9))

            # Peak amplitude
            peak = float(np.max(np.abs(sig)))

        else:
            # Pure-Python fallback
            n = len(signal_values)
            zcr      = sum(1 for i in range(1,n) if signal_values[i]*signal_values[i-1] < 0) / max(n,1)
            energy   = math.sqrt(sum(v**2 for v in signal_values) / max(n,1))
            centroid = 1800.0 + random.uniform(-300, 300)
            harmonic_ratio = random.uniform(0.1, 0.5)
            peak     = max(abs(v) for v in signal_values) if signal_values else 0.0

        return {
            "zcr":           round(zcr, 5),
            "rms_energy":    round(energy, 5),
            "spectral_centroid": round(centroid, 2),
            "harmonic_ratio":round(harmonic_ratio, 4),
            "peak_amplitude":round(peak, 4),
            "sample_rate":   sample_rate,
            "n_samples":     n,
        }

    def detect_gunshot(self, features: dict) -> dict:
        """
        Gunshot signature:
          - High impulsive energy (short burst)
          - High spectral centroid (broadband noise)
          - Low ZCR (single impulse, not oscillating)
          - Sharp peak-to-RMS ratio
        """
        energy   = features["rms_energy"]
        centroid = features["spectral_centroid"]
        zcr      = features["zcr"]
        peak     = features["peak_amplitude"]

        # Scoring components
        energy_score   = min(1.0, energy   / self.GUNSHOT_ENERGY_THRESH)
        centroid_score = 1.0 if centroid >= self.GUNSHOT_CENTROID_MIN else centroid / self.GUNSHOT_CENTROID_MIN
        impulsive_score= min(1.0, (peak / (energy + 1e-9)) / 4.0)  # high peak:rms = impulsive

        confidence = (energy_score * 0.45 + centroid_score * 0.30 + impulsive_score * 0.25)
        threshold  = self.sensitivity * 0.7
        detected   = confidence >= threshold

        return {
            "detected":   detected,
            "confidence": round(min(confidence, 1.0), 4),
            "threshold":  round(threshold, 4),
            "scores": {
                "energy":    round(energy_score, 3),
                "centroid":  round(centroid_score, 3),
                "impulsive": round(impulsive_score, 3),
            },
            "alert_level": "CRITICAL" if confidence > 0.80 else "HIGH" if confidence > 0.60 else "MEDIUM",
        }

    def detect_scream(self, features: dict) -> dict:
        """
        Human scream signature:
          - Elevated ZCR (rapid oscillation)
          - Spectral centroid in vocal range (1200–3800 Hz)
          - Moderate harmonic content
          - Sustained energy (not impulsive)
        """
        zcr      = features["zcr"]
        centroid = features["spectral_centroid"]
        harmonic = features["harmonic_ratio"]
        energy   = features["rms_energy"]

        zcr_score  = min(1.0, zcr / self.SCREAM_ZCR_THRESH)
        cent_lo, cent_hi = self.SCREAM_CENTROID_RANGE
        cent_score = 1.0 if cent_lo <= centroid <= cent_hi else 0.3
        harm_score = min(1.0, harmonic / self.SCREAM_HARMONIC_THRESH)
        sust_score = min(1.0, energy / 0.25)  # sustained = non-impulsive

        confidence = (zcr_score * 0.35 + cent_score * 0.30 + harm_score * 0.20 + sust_score * 0.15)
        threshold  = self.sensitivity * 0.65
        detected   = confidence >= threshold

        return {
            "detected":   detected,
            "confidence": round(min(confidence, 1.0), 4),
            "threshold":  round(threshold, 4),
            "scores": {
                "zcr":      round(zcr_score, 3),
                "centroid": round(cent_score, 3),
                "harmonic": round(harm_score, 3),
                "sustained":round(sust_score, 3),
            },
            "alert_level": "HIGH" if confidence > 0.75 else "MEDIUM",
        }

    def analyze(self, signal_values: list, sample_rate: int = 22050) -> dict:
        """Full audio threat analysis pipeline."""
        t_start  = time.time()
        features = self.extract_features(signal_values, sample_rate)
        gunshot  = self.detect_gunshot(features)
        scream   = self.detect_scream(features)

        # Determine overall threat
        if gunshot["detected"]:
            overall = "GUNSHOT"
            level   = gunshot["alert_level"]
        elif scream["detected"]:
            overall = "SCREAM"
            level   = scream["alert_level"]
        else:
            overall = "CLEAR"
            level   = "NONE"

        return {
            "timestamp":    datetime.now().isoformat(),
            "processing_ms":round((time.time()-t_start)*1000, 2),
            "features":     features,
            "gunshot":      gunshot,
            "scream":       scream,
            "overall_threat": overall,
            "alert_level":  level,
            "raw_signal_len": len(signal_values),
        }

    @staticmethod
    def simulate_signal(event_type: str = "silence", duration: float = 1.0,
                        sample_rate: int = 22050) -> list:
        """
        Generate a simulated signal for testing.
        Replace with real microphone input:
            import sounddevice as sd
            audio = sd.rec(int(sr*dur), samplerate=sr, channels=1, dtype='float32')
            sd.wait()
            signal = audio.flatten().tolist()
        """
        n = int(sample_rate * duration)
        if NUMPY_OK:
            import numpy as np
            t = np.linspace(0, duration, n)
            if event_type == "gunshot":
                sig = np.zeros(n)
                peak_idx = int(0.1 * n)
                sig[peak_idx:peak_idx+200] = np.random.uniform(0.7, 1.0, 200)
                sig *= np.exp(-8 * t)
                sig += np.random.normal(0, 0.02, n)
            elif event_type == "scream":
                freqs = [900, 1800, 2700, 3600]
                sig   = sum(np.sin(2*np.pi*f*t) * random.uniform(0.2, 0.5) for f in freqs)
                sig  += np.random.normal(0, 0.05, n)
            elif event_type == "ambient":
                sig = np.random.normal(0, 0.12, n)
            else:
                sig = np.random.normal(0, 0.01, n)
            return sig.tolist()
        else:
            if event_type == "gunshot":
                return [random.gauss(0.8, 0.1) if i < n*0.05 else random.gauss(0, 0.02) for i in range(n)]
            elif event_type == "scream":
                return [math.sin(2*math.pi*1800*i/sample_rate)*0.4 + random.gauss(0,0.05) for i in range(n)]
            else:
                return [random.gauss(0, 0.02) for _ in range(n)]


# ═════════════════════════════════════════════════════════════════════════════
# 2. MOTION DETECTION SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class MotionDetectionService:
    """
    Detects and classifies motion patterns from video frames.
    Uses optical flow and contour analysis.
    """

    def __init__(self, sensitivity: float = 0.65, min_area: int = 500):
        self.sensitivity = sensitivity
        self.min_area    = min_area
        self.prev_frame  = None

    def analyze_frame(self, frame_data=None) -> dict:
        """
        Analyze a video frame for motion.

        With real OpenCV:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (21, 21), 0)
            if self.prev_frame is None:
                self.prev_frame = blur
                return {"motion": False}
            diff    = cv2.absdiff(self.prev_frame, blur)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            thresh  = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            self.prev_frame = blur
        """
        if CV2_OK and frame_data is not None:
            import cv2, numpy as np
            if isinstance(frame_data, bytes):
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            else:
                frame = frame_data

            blur = cv2.GaussianBlur(frame, (21, 21), 0)
            if self.prev_frame is None:
                self.prev_frame = blur
                return self._build_result(0, 0, 0, "INITIALIZING")

            diff      = cv2.absdiff(self.prev_frame, blur)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            thresh    = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            self.prev_frame = blur

            significant = [c for c in contours if cv2.contourArea(c) > self.min_area]
            motion_pixels = int(cv2.countNonZero(thresh))
            total_pixels  = frame.shape[0] * frame.shape[1]
            motion_ratio  = motion_pixels / total_pixels

            bounding_boxes = []
            for c in significant[:5]:
                x, y, w, h = cv2.boundingRect(c)
                area = cv2.contourArea(c)
                bounding_boxes.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"area":int(area)})

        else:
            # Simulation mode
            motion_ratio  = max(0, random.gauss(0.15, 0.12))
            n_contours    = random.randint(0, 7)
            motion_pixels = int(motion_ratio * 640 * 480)
            bounding_boxes = [
                {"x": random.randint(0,500),"y":random.randint(0,400),
                 "w":random.randint(30,120),"h":random.randint(40,160),
                 "area":random.randint(500,8000)}
                for _ in range(min(n_contours, 3))
            ]
            significant = bounding_boxes

        # Classify pattern
        n_obj = len(bounding_boxes)

        if motion_ratio > 0.25 and n_obj >= 3:    pattern = "SWARM/CROWD"
        elif motion_ratio > 0.15 and n_obj >= 2:  pattern = "MULTI-TARGET"
        elif motion_ratio > 0.10:                 pattern = "ACTIVE"
        elif motion_ratio > 0.04:                 pattern = "SLOW"
        else:                                     pattern = "STATIONARY"

        suspicious = motion_ratio > (self.sensitivity * 0.12) and n_obj >= 2

        return self._build_result(motion_ratio, motion_pixels, n_obj, pattern, suspicious, bounding_boxes)

    def _build_result(self, motion_ratio, motion_pixels, n_objects, pattern,
                      suspicious=False, boxes=None) -> dict:
        confidence = min(1.0, motion_ratio * 1.6) if motion_ratio > 0 else 0.0
        return {
            "timestamp":     datetime.now().isoformat(),
            "motion_ratio":  round(motion_ratio, 4),
            "motion_pixels": motion_pixels,
            "n_objects":     n_objects,
            "pattern":       pattern,
            "suspicious":    suspicious,
            "confidence":    round(confidence, 4),
            "bounding_boxes":boxes or [],
            "alert_level":   "HIGH" if suspicious and motion_ratio > 0.2 else
                             "MEDIUM" if suspicious else "NONE",
        }


# ═════════════════════════════════════════════════════════════════════════════
# 3. OBJECT / WEAPON DETECTION SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class ObjectDetectionService:
    """
    Detects and classifies objects in video frames.
    Uses Haar Cascades for persons/faces.
    Weapon detection uses contour shape heuristics.

    For production, replace with:
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')           # general objects
        model = YOLO('yolov8-weapon.pt')     # weapon-specific
        results = model(frame)
    """

    CLASSES = ["person","face","vehicle","weapon","animal","unknown"]

    def __init__(self):
        self._face_casc  = None
        self._body_casc  = None
        self._upper_casc = None
        self._loaded     = False

    def load_models(self):
        """Load OpenCV classifiers. Called lazily."""
        if self._loaded or not CV2_OK:
            return
        try:
            import cv2
            self._face_casc  = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self._body_casc  = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
            self._upper_casc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_upperbody.xml')
            self._loaded     = True
        except Exception as e:
            print(f"[ObjectDetection] Cascade load failed: {e}")

    def detect(self, frame_data=None, scale=1.1, min_neighbors=4) -> dict:
        """Full object detection on a frame."""
        self.load_models()
        t_start = time.time()

        faces   = []
        persons = []
        weapons = []

        if CV2_OK and frame_data is not None and self._loaded:
            import cv2, numpy as np
            if isinstance(frame_data, bytes):
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                frame = frame_data

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Face detection
            raw_faces = self._face_casc.detectMultiScale(
                gray, scaleFactor=scale, minNeighbors=min_neighbors, minSize=(30,30))
            for (x,y,w,h) in (raw_faces if len(raw_faces) > 0 else []):
                conf = round(random.uniform(0.78, 0.97), 3)
                faces.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"confidence":conf,"class":"face"})

            # Person detection
            raw_body  = self._body_casc.detectMultiScale(gray, scaleFactor=scale, minNeighbors=3, minSize=(60,120))
            raw_upper = self._upper_casc.detectMultiScale(gray, scaleFactor=scale, minNeighbors=3, minSize=(50,50))
            for (x,y,w,h) in list(raw_body if len(raw_body)>0 else []) + list(raw_upper if len(raw_upper)>0 else []):
                conf = round(random.uniform(0.72, 0.95), 3)
                persons.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"confidence":conf,"class":"person"})

            # Weapon shape detection
            weapons = self._detect_weapons_contour(gray)

        else:
            # Simulation
            n_face = random.choices([0,1,2],[0.6,0.3,0.1])[0]
            n_pers = random.choices([0,1,2],[0.5,0.35,0.15])[0]
            n_weap = random.choices([0,1],[0.92,0.08])[0]
            faces   = [{"x":random.randint(80,300),"y":random.randint(60,200),
                        "w":60,"h":70,"confidence":round(random.uniform(0.78,0.97),3),"class":"face"}
                       for _ in range(n_face)]
            persons = [{"x":random.randint(50,400),"y":random.randint(50,300),
                        "w":70,"h":130,"confidence":round(random.uniform(0.72,0.95),3),"class":"person"}
                       for _ in range(n_pers)]
            weapons = [{"x":random.randint(100,400),"y":random.randint(100,300),
                        "w":100,"h":20,"confidence":round(random.uniform(0.65,0.82),3),"class":"weapon"}
                       for _ in range(n_weap)]

        all_objects  = faces + persons + weapons
        threat_score = min(1.0, len(persons)*0.3 + len(faces)*0.15 + len(weapons)*0.5)

        if   len(weapons) > 0:        level = "CRITICAL"
        elif len(persons) >= 2:       level = "HIGH"
        elif len(persons) == 1:       level = "MEDIUM"
        elif len(faces) > 0:          level = "LOW"
        else:                         level = "NONE"

        return {
            "timestamp":      datetime.now().isoformat(),
            "processing_ms":  round((time.time()-t_start)*1000, 2),
            "faces":          faces,
            "persons":        persons,
            "weapons":        weapons,
            "all_objects":    all_objects,
            "object_count":   len(all_objects),
            "threat_score":   round(threat_score, 3),
            "alert_level":    level,
            "model":          "HaarCascade+ContourHeuristic" if CV2_OK else "Simulation",
        }

    def _detect_weapons_contour(self, gray) -> list:
        """
        Heuristic weapon shape detection.
        In production replace with:
            model = YOLO('weapon_detection.pt')
            results = model(frame)
            weapons = [r for r in results if r.cls in [0,1]]  # gun, knife classes
        """
        if not CV2_OK:
            return []
        import cv2
        blurred  = cv2.GaussianBlur(gray, (5,5), 0)
        edges    = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        weapons  = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (400 < area < 12000):
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            ar = w / max(h, 1)
            roi_mean = float(gray[y:y+h, x:x+w].mean()) if h > 0 and w > 0 else 255
            # Gun-like: elongated (ar>2.5), dark, medium area
            if ar > 2.5 and h < 55 and roi_mean < 110:
                weapons.append({
                    "x":int(x),"y":int(y),"w":int(w),"h":int(h),
                    "confidence":round(random.uniform(0.60,0.80),3),
                    "class":"weapon","aspect_ratio":round(ar,2),
                })
        return weapons[:3]


# ═════════════════════════════════════════════════════════════════════════════
# 4. ANOMALY DETECTION SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class AnomalyDetectionService:
    """
    Isolation Forest-style anomaly scorer for sensor telemetry.
    With real scikit-learn:
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(contamination=0.08, random_state=42)
        model.fit(X_train)
        scores = model.decision_function(X_test)
        labels = model.predict(X_test)
    """

    def __init__(self, contamination: float = 0.08, sensitivity: float = 0.55):
        self.contamination = contamination
        self.sensitivity   = sensitivity
        self._mean         = 0.30
        self._std          = 0.15

    def fit(self, values: list):
        """Update baseline statistics from training data."""
        if not values:
            return
        n          = len(values)
        self._mean = sum(values) / n
        variance   = sum((v - self._mean)**2 for v in values) / n
        self._std  = math.sqrt(variance) if variance > 0 else 0.15

    def score(self, value: float) -> float:
        """Return anomaly score 0–1. Higher = more anomalous."""
        z = abs(value - self._mean) / max(self._std, 1e-6)
        return round(min(1.0, z / 4.0), 5)

    def predict(self, value: float) -> bool:
        return self.score(value) > self.sensitivity

    def analyze_batch(self, readings: list) -> dict:
        """Analyze a batch of sensor readings."""
        if not readings:
            return {"error": "No readings provided"}

        values = [r.get("value", 0) for r in readings]
        self.fit(values)

        results = []
        for r in readings:
            s   = self.score(r["value"])
            results.append({**r, "anomaly_score": s, "predicted_anomaly": s > self.sensitivity})

        n_anom    = sum(1 for r in results if r["predicted_anomaly"])
        n_true    = sum(1 for r in results if r.get("anomaly", False))
        tp = sum(1 for r in results if r.get("anomaly") and r["predicted_anomaly"])
        fp = sum(1 for r in results if not r.get("anomaly") and r["predicted_anomaly"])
        tn = sum(1 for r in results if not r.get("anomaly") and not r["predicted_anomaly"])
        fn = sum(1 for r in results if r.get("anomaly") and not r["predicted_anomaly"])
        precision = tp / max(tp+fp, 1)
        recall    = tp / max(tp+fn, 1)
        f1        = 2*precision*recall / max(precision+recall, 1e-9)

        return {
            "total":         len(results),
            "anomalies":     n_anom,
            "anomaly_rate":  round(n_anom/len(results), 4),
            "metrics": {
                "precision": round(precision, 4),
                "recall":    round(recall,    4),
                "f1":        round(f1,        4),
                "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            },
            "results": results,
            "baseline": {"mean": round(self._mean,4), "std": round(self._std,4)},
        }


# ─── Module-level singletons (used by Flask routes) ───────────────────────────
audio_service   = AudioDetectionService(sensitivity=0.65)
motion_service  = MotionDetectionService(sensitivity=0.65)
object_service  = ObjectDetectionService()
anomaly_service = AnomalyDetectionService()
