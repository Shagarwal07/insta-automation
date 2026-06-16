import os
import streamlit as st
from core_engine import init_db, migrate_db, clean_handles, get_posts
from theme import THEME_CSS, HERO_HTML

st.set_page_config(page_title="Gayu_theHelper", page_icon="🌸", layout="wide", initial_sidebar_state="collapsed")

init_db()
migrate_db()

st.markdown(THEME_CSS, unsafe_allow_html=True)
st.markdown(HERO_HTML, unsafe_allow_html=True)

# ── TOP NAV ──
pages = {
    "🏠 Dashboard":    "app",
    "🔍 Discovery":    "pages/1_Discovery",
    "📦 Import JSON":  "pages/2_Import",
    "✍️ Captions":     "pages/3_Captions",
    "🎨 Creative":     "pages/4_Creative",
    "📊 Analytics":    "pages/5_Analytics",
}

selected = st.query_params.get("page", "dashboard")

nav_html = '<div class="nav-menu">'
for label, key in {
    "🏠 Dashboard": "dashboard",
    "🔍 Discovery": "discovery",
    "📦 Import JSON": "import",
    "✍️ Captions": "captions",
    "🎨 Creative": "creative",
    "📊 Analytics": "analytics",
}.items():
    active = "active" if selected == key else ""
    nav_html += f'<a class="nav-btn {active}" href="?page={key}">{label}</a>'
nav_html += '</div>'
st.markdown(nav_html, unsafe_allow_html=True)

st.markdown("---")

# ── DASHBOARD CONTENT ──
if selected == "dashboard":
    handles_input = st.text_input("Instagram Handle", value="@gayatribhardwaj__")
    handles = clean_handles(handles_input)
    posts = get_posts(handles)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✨ Total Posts", len(posts))
    c2.metric("🔥 Viral Picks", sum(1 for p in posts if p[7] >= 80))
    c3.metric("💬 Synced", len([p for p in posts if p[6] != "SKIPPED"]))
    c4.metric("🌸 Skipped", len([p for p in posts if p[6] == "SKIPPED"]))

    st.markdown("### 💖 Suggested Content")
    if not posts:
        st.info("No posts found. Go to 🔍 Discovery to sync data first.")
    else:
        for row in posts[:10]:
            post_id, handle, shortcode, url, post_type, saved_mode, status, viral_score, engagement_rating, category, reason, gemini_caption = row
            score_color = "#e8006e" if viral_score >= 80 else "#f4a261" if viral_score >= 60 else "#8d99ae"
            st.markdown(f"""
            <div class='card'>
                <b style='color:#e8006e;'>@{handle}</b> &nbsp;·&nbsp; {post_type} &nbsp;·&nbsp;
                <b style='color:{score_color};'>{viral_score}/100</b> &nbsp;·&nbsp; {engagement_rating}<br>
                <small style='color:#666;'>{reason}</small><br>
                <div style='background:rgba(255,240,248,0.9);padding:12px;border-radius:12px;margin-top:8px;font-style:italic;'>
                    ✨ {gemini_caption}
                </div>
                <small>🔗 {url}</small>
            </div>
            """, unsafe_allow_html=True)

elif selected == "discovery":
    st.switch_page("pages/1_Discovery.py")
elif selected == "import":
    st.switch_page("pages/2_Import.py")
elif selected == "captions":
    st.switch_page("pages/3_Captions.py")
elif selected == "creative":
    st.switch_page("pages/4_Creative.py")
elif selected == "analytics":
    st.switch_page("pages/5_Analytics.py")
