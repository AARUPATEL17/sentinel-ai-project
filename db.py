"""
database/db.py — SQLite Database Layer
Stores: users, alerts, locations, incidents, chatbot_logs
Works 100% offline with Python's built-in sqlite3.
In production, swap the connection string for MySQL/Firebase.
"""

import sqlite3, hashlib, os, json
from datetime import datetime

# Always resolve DB path relative to this file — works on Windows & Linux
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentinel.db")


# ── Connection helper ──────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema init ───────────────────────────────────────────────────────────────
def init_db():
    conn = get_conn()
    c    = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role        TEXT DEFAULT 'officer',   -- admin | officer
        name        TEXT,
        badge       TEXT,
        sector      TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        last_login  TEXT,
        active      INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS alerts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        level       TEXT NOT NULL,            -- CRITICAL|HIGH|MEDIUM|LOW
        type        TEXT NOT NULL,            -- gunshot|scream|motion|intrusion|weapon
        sector      TEXT,
        message     TEXT,
        lat         REAL,
        lon         REAL,
        score       REAL,
        source      TEXT,                     -- camera|audio|sensor|manual
        resolved    INTEGER DEFAULT 0,
        resolved_by TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        resolved_at TEXT
    );

    CREATE TABLE IF NOT EXISTS locations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id     TEXT NOT NULL,            -- UNIT-1, DRONE-2, etc.
        unit_type   TEXT DEFAULT 'officer',   -- officer|drone|vehicle
        lat         REAL NOT NULL,
        lon         REAL NOT NULL,
        sector      TEXT,
        speed       REAL DEFAULT 0,
        heading     REAL DEFAULT 0,
        status      TEXT DEFAULT 'active',
        recorded_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS incidents (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT UNIQUE,
        date        TEXT,
        sector      TEXT,
        type        TEXT,
        severity    TEXT,
        outcome     TEXT,
        description TEXT,
        lat         REAL,
        lon         REAL,
        duration_min INTEGER,
        responders  INTEGER,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS chatbot_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT,
        role        TEXT,                     -- user | assistant
        message     TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id    INTEGER,
        channel     TEXT,                     -- sms|email|push
        recipient   TEXT,
        status      TEXT DEFAULT 'pending',   -- pending|sent|failed
        sent_at     TEXT,
        error       TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    );
    """)

    # Seed admin + officer accounts if empty
    existing = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        for uname, pwd, role, name, badge in [
            ("admin",   "admin123",   "admin",   "Admin User",       "ADM-001"),
            ("officer1","officer123", "officer", "Rajesh Kumar",     "OFF-101"),
            ("officer2","officer123", "officer", "Priya Sharma",     "OFF-102"),
            ("officer3","officer123", "officer", "Vikram Singh",     "OFF-103"),
        ]:
            c.execute(
                "INSERT INTO users (username,password_hash,role,name,badge,sector) VALUES (?,?,?,?,?,?)",
                (uname, _hash(pwd), role, name, badge, "B2")
            )

    conn.commit()
    conn.close()


def _hash(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


# ── User functions ─────────────────────────────────────────────────────────────
def authenticate(username: str, password: str):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=? AND active=1",
        (username, _hash(password))
    ).fetchone()
    if row:
        conn.execute("UPDATE users SET last_login=? WHERE id=?",
                     (datetime.now().isoformat(), row["id"]))
        conn.commit()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn  = get_conn()
    rows  = conn.execute("SELECT * FROM users ORDER BY role,name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_user(username, password, role, name, badge, sector=""):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users (username,password_hash,role,name,badge,sector) VALUES (?,?,?,?,?,?)",
            (username, _hash(password), role, name, badge, sector)
        )
        conn.commit()
        conn.close()
        return True, "User created"
    except sqlite3.IntegrityError:
        return False, "Username already exists"


def toggle_user(user_id: int, active: int):
    conn = get_conn()
    conn.execute("UPDATE users SET active=? WHERE id=?", (active, user_id))
    conn.commit()
    conn.close()


# ── Alert functions ────────────────────────────────────────────────────────────
def insert_alert(level, atype, sector, message, lat=None, lon=None,
                 score=0.0, source="sensor"):
    conn = get_conn()
    c    = conn.cursor()
    c.execute(
        """INSERT INTO alerts
           (level,type,sector,message,lat,lon,score,source)
           VALUES (?,?,?,?,?,?,?,?)""",
        (level, atype, sector, message, lat, lon, round(score,3), source)
    )
    alert_id = c.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def get_alerts(limit=50, level=None, resolved=None):
    conn  = get_conn()
    query = "SELECT * FROM alerts WHERE 1=1"
    args  = []
    if level:    query += " AND level=?";    args.append(level)
    if resolved is not None:
        query += " AND resolved=?"; args.append(resolved)
    query += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    rows  = conn.execute(query, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_alert(alert_id: int, resolved_by: str):
    conn = get_conn()
    conn.execute(
        "UPDATE alerts SET resolved=1, resolved_by=?, resolved_at=? WHERE id=?",
        (resolved_by, datetime.now().isoformat(), alert_id)
    )
    conn.commit()
    conn.close()


def get_alert_stats():
    conn  = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    crit  = conn.execute("SELECT COUNT(*) FROM alerts WHERE level='CRITICAL'").fetchone()[0]
    unres = conn.execute("SELECT COUNT(*) FROM alerts WHERE resolved=0").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE date(created_at)=date('now')"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "critical": crit, "unresolved": unres, "today": today}


# ── Location functions ─────────────────────────────────────────────────────────
def upsert_location(unit_id, unit_type, lat, lon, sector="", speed=0, heading=0, status="active"):
    conn = get_conn()
    conn.execute(
        """INSERT INTO locations (unit_id,unit_type,lat,lon,sector,speed,heading,status,recorded_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (unit_id, unit_type, lat, lon, sector, speed, heading, status, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_latest_locations():
    conn = get_conn()
    rows = conn.execute("""
        SELECT l.* FROM locations l
        INNER JOIN (
            SELECT unit_id, MAX(recorded_at) as max_t FROM locations GROUP BY unit_id
        ) m ON l.unit_id=m.unit_id AND l.recorded_at=m.max_t
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_location_history(unit_id, limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM locations WHERE unit_id=? ORDER BY recorded_at DESC LIMIT ?",
        (unit_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Chatbot log functions ──────────────────────────────────────────────────────
def save_chat(session_id: str, role: str, message: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO chatbot_logs (session_id,role,message) VALUES (?,?,?)",
        (session_id, role, message)
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id: str, limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT role,message,created_at FROM chatbot_logs WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))


# ── Notification log ───────────────────────────────────────────────────────────
def log_notification(alert_id, channel, recipient, status, error=None):
    conn = get_conn()
    conn.execute(
        """INSERT INTO notifications (alert_id,channel,recipient,status,sent_at,error)
           VALUES (?,?,?,?,?,?)""",
        (alert_id, channel, recipient, status, datetime.now().isoformat(), error)
    )
    conn.commit()
    conn.close()


def get_notification_logs(limit=30):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Report helpers ─────────────────────────────────────────────────────────────
def get_alerts_by_type():
    conn = get_conn()
    rows = conn.execute(
        "SELECT type, COUNT(*) as cnt FROM alerts GROUP BY type ORDER BY cnt DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_alerts_by_sector():
    conn = get_conn()
    rows = conn.execute(
        "SELECT sector, COUNT(*) as cnt FROM alerts GROUP BY sector ORDER BY cnt DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_alert_counts(days=14):
    conn = get_conn()
    rows = conn.execute(
        """SELECT date(created_at) as day, COUNT(*) as cnt
           FROM alerts WHERE date(created_at) >= date('now', ?)
           GROUP BY day ORDER BY day""",
        (f"-{days} days",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialise on import
init_db()
