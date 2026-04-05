"""
api/services/auth_service.py
──────────────────────────────
Backend auth service:
  • Password hashing (SHA-256 / bcrypt)
  • JWT token generation and verification
  • Session management
  • Role-based access control
  • Login attempt tracking (brute-force protection)

In production:
    pip install flask-jwt-extended bcrypt
"""

import hashlib, hmac, base64, json, time, os, secrets
from datetime import datetime, timedelta
from typing import Optional

import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
from database.db import authenticate, get_all_users

# Try JWT
try:
    import jwt as pyjwt
    JWT_OK = True
except ImportError:
    JWT_OK = False

# Try bcrypt
try:
    import bcrypt
    BCRYPT_OK = True
except ImportError:
    BCRYPT_OK = False

SECRET_KEY = os.getenv("FLASK_SECRET", "sentinel-dev-secret-change-in-production")


class AuthService:
    """Handles all authentication and authorisation logic."""

    # Track login attempts per username for brute-force protection
    _login_attempts: dict = {}
    MAX_ATTEMPTS    = 5
    LOCKOUT_SECONDS = 300  # 5 minutes

    # Active sessions: token -> user_dict
    _sessions: dict = {}

    # ── Password hashing ──────────────────────────────────────────────────────
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password.
        Uses bcrypt if available (recommended for production),
        falls back to SHA-256.
        """
        if BCRYPT_OK:
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        if BCRYPT_OK and hashed.startswith("$2"):
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        return hashlib.sha256(plain.encode()).hexdigest() == hashed

    # ── JWT tokens ────────────────────────────────────────────────────────────
    @staticmethod
    def generate_token(user: dict, expires_hours: int = 8) -> str:
        """
        Generate a JWT access token.
        With flask-jwt-extended:
            from flask_jwt_extended import create_access_token
            return create_access_token(identity=user["id"])
        """
        if JWT_OK:
            payload = {
                "sub":      user["id"],
                "username": user["username"],
                "role":     user["role"],
                "name":     user.get("name",""),
                "exp":      datetime.utcnow() + timedelta(hours=expires_hours),
                "iat":      datetime.utcnow(),
                "jti":      secrets.token_hex(16),
            }
            return pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
        else:
            # Simple base64 fallback (NOT for production without JWT lib)
            payload = {
                "sub":      user["id"],
                "username": user["username"],
                "role":     user["role"],
                "exp":      time.time() + expires_hours * 3600,
            }
            encoded = base64.b64encode(json.dumps(payload).encode()).decode()
            sig     = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
            return f"{encoded}.{sig}"

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Verify and decode a JWT token.
        Returns payload dict or None if invalid/expired.
        """
        if not token:
            return None
        if JWT_OK:
            try:
                return pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            except pyjwt.ExpiredSignatureError:
                return None
            except pyjwt.InvalidTokenError:
                return None
        else:
            try:
                parts  = token.split(".")
                if len(parts) != 2:
                    return None
                encoded, sig = parts
                expected_sig = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(sig, expected_sig):
                    return None
                payload = json.loads(base64.b64decode(encoded.encode()).decode())
                if payload.get("exp", 0) < time.time():
                    return None
                return payload
            except Exception:
                return None

    # ── Login ─────────────────────────────────────────────────────────────────
    def login(self, username: str, password: str) -> dict:
        """
        Authenticate a user and return a token.
        Includes brute-force protection.
        """
        # Check lockout
        attempt_key = username.lower()
        attempts    = self._login_attempts.get(attempt_key, {"count":0,"last":0,"locked":False})
        if attempts.get("locked"):
            elapsed = time.time() - attempts["last"]
            if elapsed < self.LOCKOUT_SECONDS:
                remaining = int(self.LOCKOUT_SECONDS - elapsed)
                return {"success":False,"error":f"Account locked. Try again in {remaining}s.",
                        "locked":True}
            else:
                # Reset after lockout expires
                self._login_attempts[attempt_key] = {"count":0,"last":0,"locked":False}

        # Authenticate against DB
        user = authenticate(username, password)
        if not user:
            # Record failed attempt
            attempts["count"] = attempts.get("count",0) + 1
            attempts["last"]  = time.time()
            if attempts["count"] >= self.MAX_ATTEMPTS:
                attempts["locked"] = True
            self._login_attempts[attempt_key] = attempts
            remaining = self.MAX_ATTEMPTS - attempts["count"]
            return {"success":False, "error":"Invalid credentials",
                    "attempts_remaining": max(0, remaining)}

        # Success — reset attempts
        self._login_attempts.pop(attempt_key, None)

        token = self.generate_token(user)
        user.pop("password_hash", None)

        # Store session
        self._sessions[token] = {
            "user":       user,
            "created_at": datetime.now().isoformat(),
            "last_active":datetime.now().isoformat(),
        }

        return {
            "success":    True,
            "token":      token,
            "user":       user,
            "expires_in": "8 hours",
            "token_type": "Bearer",
        }

    def logout(self, token: str) -> dict:
        """Invalidate a token."""
        removed = self._sessions.pop(token, None)
        return {"success": True, "message": "Logged out" if removed else "Token not found"}

    def get_session(self, token: str) -> Optional[dict]:
        """Get active session for a token."""
        session = self._sessions.get(token)
        if session:
            session["last_active"] = datetime.now().isoformat()
        return session

    # ── RBAC helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def require_role(payload: dict, required_role: str) -> bool:
        """Check if token payload has required role."""
        role = payload.get("role","")
        if required_role == "admin":
            return role == "admin"
        return role in ("admin","officer")

    @staticmethod
    def get_permissions(role: str) -> dict:
        """Return permission set for a role."""
        base = {
            "view_dashboard":   True,
            "view_alerts":      True,
            "view_camera":      True,
            "view_map":         True,
            "create_alerts":    True,
            "resolve_alerts":   True,
            "view_reports":     True,
            "use_chatbot":      True,
            "manage_users":     False,
            "delete_alerts":    False,
            "view_all_logs":    False,
            "change_settings":  False,
        }
        if role == "admin":
            return {k: True for k in base}
        return base

    # ── API key auth (for sensor nodes) ──────────────────────────────────────
    _api_keys = {
        "sensor-node-key-001": {"unit":"SENSOR-GRID-A","role":"sensor"},
        "drone-key-002":       {"unit":"DRONE-FLEET",  "role":"drone"},
    }

    def verify_api_key(self, key: str) -> Optional[dict]:
        return self._api_keys.get(key)


# ─── Singleton ────────────────────────────────────────────────────────────────
auth_service = AuthService()
