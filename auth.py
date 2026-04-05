"""
auth.py — Login System with session management
Admin / Officer roles, logout, user management.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db import authenticate, get_all_users, add_user, toggle_user

def check_login() -> bool:
    """Returns True if user is logged in. Shows login page otherwise."""
    if st.session_state.get("logged_in"):
        return True
    _show_login_page()
    return False

def get_user() -> dict:
    return st.session_state.get("current_user", {})

def is_admin() -> bool:
    return get_user().get("role") == "admin"

def _show_login_page():
    # Full-page login
    st.markdown("""
    <style>
    .stApp { background:#020b0f !important; }
    [data-testid="stSidebar"] { display:none !important; }
    </style>
    <div style="max-width:460px;margin:60px auto 0;">
      <div style="text-align:center;margin-bottom:40px;">
        <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:64px;
                    letter-spacing:12px;color:#00e5ff;text-shadow:0 0 40px rgba(0,229,255,0.4);">
          SENTINEL</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                    color:#5d8a99;margin-top:4px;">BORDER DEFENCE AI PLATFORM</div>
        <div style="width:60%;height:1px;background:rgba(0,229,255,0.15);margin:20px auto;"></div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:3px;
                    color:#ff6b35;">🔐 SECURE ACCESS REQUIRED</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("Username", placeholder="admin / officer1 / officer2")
        password = st.text_input("Password", type="password", placeholder="••••••••••")

        if st.button("🔓 LOGIN", use_container_width=True, type="primary"):
            user = authenticate(username.strip(), password.strip())
            if user:
                st.session_state.logged_in    = True
                st.session_state.current_user = user
                st.success(f"✅ Welcome, {user['name']} [{user['role'].upper()}]")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

        st.markdown("""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);padding:16px;margin-top:16px;
                    font-family:'Share Tech Mono',monospace;font-size:11px;line-height:2;color:#5d8a99;">
          <div style="color:#00e5ff;margin-bottom:6px;letter-spacing:2px;">DEFAULT CREDENTIALS</div>
          admin / admin123 &nbsp;&nbsp; <span style="color:#ff6b35;">[ADMIN]</span><br>
          officer1 / officer123 <span style="color:#5d8a99;">[OFFICER]</span><br>
          officer2 / officer123 <span style="color:#5d8a99;">[OFFICER]</span>
        </div>
        """, unsafe_allow_html=True)


def show_user_management():
    """Admin-only user management page."""
    st.markdown("""
    <div style="margin-bottom:24px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;
                  color:#ff6b35;text-transform:uppercase;margin-bottom:8px;">// 07 — ACCESS CONTROL</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;
                  text-transform:uppercase;letter-spacing:-1px;color:#cce8f0;line-height:1;">USER MANAGEMENT</div>
    </div>""", unsafe_allow_html=True)

    if not is_admin():
        st.error("⛔ Admin access required.")
        return

    tabs = st.tabs(["👥 ALL USERS", "➕ ADD USER"])

    with tabs[0]:
        users = get_all_users()
        lc_role = {"admin":"#ff6b35","officer":"#00e5ff"}
        rows_html = ""
        for u in users:
            c   = lc_role.get(u["role"],"#cce8f0")
            act = "✓ ACTIVE" if u["active"] else "✗ DISABLED"
            act_color = "#39ff14" if u["active"] else "#ff1744"
            rows_html += f"""
            <div style="display:grid;grid-template-columns:80px 1fr 80px 80px 80px 100px 120px;
                        gap:8px;padding:10px 14px;border-left:3px solid {c};
                        background:rgba(0,0,0,0.3);margin-bottom:2px;
                        font-family:'Share Tech Mono',monospace;font-size:11px;">
              <span style="color:#5d8a99;">#{u['id']}</span>
              <span style="color:#cce8f0;">{u['name']}</span>
              <span style="color:#5d8a99;">{u['username']}</span>
              <span style="color:{c};">{u['role'].upper()}</span>
              <span style="color:#5d8a99;">{u['badge']}</span>
              <span style="color:{act_color};">{act}</span>
              <span style="color:#5d8a99;">{(u.get('last_login') or 'Never')[:16]}</span>
            </div>"""
        st.markdown(f"""
        <div style="background:#061520;border:1px solid rgba(0,229,255,0.12);padding:8px;">
          <div style="display:grid;grid-template-columns:80px 1fr 80px 80px 80px 100px 120px;
                      gap:8px;padding:8px 14px;font-family:'Share Tech Mono',monospace;font-size:9px;
                      letter-spacing:2px;color:#5d8a99;border-bottom:1px solid rgba(0,229,255,0.1);margin-bottom:4px;">
            <span>ID</span><span>NAME</span><span>USER</span><span>ROLE</span>
            <span>BADGE</span><span>STATUS</span><span>LAST LOGIN</span>
          </div>{rows_html}
        </div>""", unsafe_allow_html=True)

        # Toggle active
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        tog_id  = col1.number_input("User ID to toggle", min_value=1, value=2)
        tog_act = col2.selectbox("Set status", ["active","disabled"])
        if col3.button("APPLY"):
            toggle_user(int(tog_id), 1 if tog_act=="active" else 0)
            st.success("Updated")
            st.rerun()

    with tabs[1]:
        col1, col2 = st.columns(2)
        new_name  = col1.text_input("Full Name")
        new_badge = col2.text_input("Badge Number")
        new_user  = col1.text_input("Username")
        new_pass  = col2.text_input("Password", type="password")
        new_role  = col1.selectbox("Role", ["officer","admin"])
        new_sec   = col2.selectbox("Sector", ["A1","A2","B1","B2","B3","C1","C2","C3","D1"])

        if st.button("➕ CREATE USER", type="primary"):
            if new_user and new_pass and new_name:
                ok, msg = add_user(new_user, new_pass, new_role, new_name, new_badge, new_sec)
                if ok: st.success(f"✅ {msg}")
                else:  st.error(f"❌ {msg}")
            else:
                st.warning("Fill all required fields")


def show_logout_button():
    """Shows logout in sidebar."""
    user = get_user()
    st.sidebar.markdown(f"""
    <div style="background:#061520;border:1px solid rgba(0,229,255,0.1);padding:12px 16px;margin-top:8px;">
      <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:2px;color:#5d8a99;">LOGGED IN AS</div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:12px;color:#00e5ff;margin-top:4px;">{user.get('name','')}</div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:#ff6b35;">{user.get('role','').upper()} · {user.get('badge','')}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("🔒 LOGOUT", use_container_width=True):
        for k in ["logged_in","current_user","chat_messages","chat_session"]:
            st.session_state.pop(k, None)
        st.rerun()
