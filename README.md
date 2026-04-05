# 🛡️ SENTINEL v3.0 — Border Defence AI Platform
### Full-Stack · 10 Pages · Real Camera · GPS Map · AI Chatbot · SMS/Email · SQLite DB · Flask API

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (app.py)                     │
│  Login → Dashboard → Camera → AI Detect → Chatbot → Alerts  │
└───────────────────────┬─────────────────────────────────────┘
                        │  HTTP / Direct import
              ┌─────────▼──────────┐
              │  Flask API Backend  │  ← api/flask_api.py
              │  (api/client.py)   │     Run: python api/flask_api.py
              └─────────┬──────────┘
                        │  sqlite3
              ┌─────────▼──────────┐
              │    SQLite Database  │  ← database/sentinel.db
              │   (database/db.py) │
              └────────────────────┘
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Start Flask API in a separate terminal
```bash
python api/flask_api.py
# Runs at http://127.0.0.1:5050
# Streamlit works without it (uses DB directly as fallback)
```

### 3. Run Streamlit
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### 4. Login
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| officer1 | officer123 | Officer |
| officer2 | officer123 | Officer |

---

## 📁 Project Structure

```
sentinel_v3/
├── app.py                        ← Main entry point (run this)
├── auth.py                       ← Login system / session / logout
├── backend.py                    ← ML engine (anomaly detection, risk)
├── requirements.txt
├── .env.example                  ← Copy to .env with your credentials
│
├── api/
│   ├── flask_api.py              ← Flask REST API (optional separate service)
│   └── client.py                 ← API client (Streamlit ↔ Flask / DB)
│
├── database/
│   ├── db.py                     ← SQLite schema + all DB functions
│   └── sentinel.db               ← Auto-created on first run
│
└── pages_src/
    ├── main_dashboard.py         ← 📊 Live dashboard with DB data
    ├── ai_threat.py              ← 🔍 Gunshot / Scream / Motion AI
    ├── camera_surveillance.py    ← 🎥 CCTV + Unknown Person + Weapon
    ├── gpsmap.py                 ← 🌐 Interactive Folium GPS map
    ├── emergency_alerts.py       ← 🚨 SMS (Twilio) + Email (SMTP)
    ├── chatbot.py                ← 🤖 AI chatbot (Claude / GPT-4 / rule-based)
    ├── realtime.py               ← 📡 Live telemetry simulation
    ├── riskmap.py                ← 🗺️ Predictive risk zones
    └── datasets.py               ← 📦 Generate & download datasets
```

---

## 🆕 Features (v3.0)

### 🔍 AI Threat Detection
- **Gunshot detection** — impulse energy + ZCR + spectral centroid analysis
- **Scream detection** — harmonic frequency pattern recognition
- **Motion detection** — OpenCV frame differencing + contour analysis
- Auto-saves detections to **SQLite database**
- Shows real-time waveform visualizer
- One-click **librosa** upgrade path for real microphone audio

### 🎥 Camera Surveillance
- Real **OpenCV webcam** capture
- **Haar Cascade** detection: faces, full body, upper body
- **Weapon shape heuristic** — contour aspect ratio + brightness analysis
- Tactical **HUD overlay** with bounding boxes, threat level, REC indicator
- Auto-creates DB alerts when threats detected
- Demo mode SVG when OpenCV not installed

### 🚨 Emergency Alert System
- **Real SMS** via Twilio API (`pip install twilio` + credentials)
- **Real Email** via Python `smtplib` (Gmail App Password)
- **Auto-dispatch** rules — send SMS on CRITICAL, email on HIGH+
- Full **notification log** stored in SQLite
- Credentials setup guide built-in

### 🤖 AI Chatbot
- Powered by **Claude (Anthropic)** or **OpenAI GPT-4**
- **Live DB context** injected into every prompt (alerts, risk zones, stats)
- **Rule-based fallback** — works with zero API key
- Chat history saved to SQLite
- Export chat log as text file

### 🗺️ GPS Live Map
- Real **Folium** interactive map (OpenStreetMap)
- Sector rectangles colour-coded by ML risk
- Incident markers, sensor nodes, patrol routes
- Border line overlay, click coordinates

### 🧾 SQLite Database
Tables: `users` · `alerts` · `locations` · `incidents` · `chatbot_logs` · `notifications`

### 🔐 Login System
- SHA-256 password hashing
- **Admin** (full access + user management)
- **Officer** (operational pages only)
- Session management with logout
- Last login tracking

### 📊 Dashboard
- DB-backed live alert queue
- AI threat analysis summary
- Sector risk grid (4×3)
- Reports: by type, by sector, daily trend

### 🔌 Flask API (Optional)
Run `python api/flask_api.py` for full REST API:
```
GET  /api/health
POST /api/auth/login
GET  /api/alerts?level=CRITICAL&resolved=0
POST /api/alerts
PUT  /api/alerts/<id>/resolve
GET  /api/alerts/stats
GET  /api/locations
POST /api/locations
GET  /api/ai/threat-analyze
POST /api/notify/sms
POST /api/notify/email
GET  /api/reports/summary
GET  /api/users
POST /api/users
```
Streamlit **auto-detects** if Flask is running and routes through it; falls back to direct DB otherwise.

---

## 🔧 Enable Real Features

| Feature | Command | Config |
|---------|---------|--------|
| Real SMS | `pip install twilio` | Add Twilio SID/Token in Emergency Alerts page |
| Real Email | Built-in smtplib | Add Gmail App Password |
| AI Chatbot | `pip install anthropic` or `openai` | Add API key in Chatbot settings |
| Real Audio | `pip install librosa sounddevice` | Uncomment librosa code in ai_threat.py |
| Real Camera | `pip install opencv-python-headless` | Select camera index |
| GPS Map | `pip install folium streamlit-folium` | Auto-enabled |
| MySQL | `pip install mysql-connector-python` | Swap connection in database/db.py |

---

## 🔒 Security Notes
- Store all credentials in `.env` (never commit to git)
- Add `.env` to `.gitignore`
- Change default passwords before deployment
- Use HTTPS in production (nginx reverse proxy recommended)
