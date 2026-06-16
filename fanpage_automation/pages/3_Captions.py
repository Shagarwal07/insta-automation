import streamlit as st
from core_engine import (
    generate_caption_variants, generate_hashtag_pack,
    detect_post_type, generate_caption,
    send_message_to_telegram, download_photo_post, send_carousel_to_telegram
)
from theme import THEME_CSS

st.set_page_config(page_title="Captions · Gayu_theHelper", page_icon="✍️", layout="wide", initial_sidebar_state="collapsed")
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.markdown("<a href='/' style='color:#e8006e;font-weight:600;text-decoration:none;'>← Back to Dashboard</a>", unsafe_allow_html=True)

# ── QUICK URL ──
st.markdown("## 🔗 Quick URL Fetch")
col1, col2 = st.columns([3, 1])
with col1:
    direct_url = st.text_input("Paste Instagram Post/Reel URL", placeholder="https://www.instagram.com/p/XXXXX/")
with col2:
    style = st.selectbox("Style", ["Dreamy", "Main Character", "Trending"])
    content_mode = st.selectbox("Mode", ["Photo Posts", "Solo Pics Only", "High Engagement Photos", "Reels Only"])

if st.button("✨ Fetch & Send", key="fetch_send"):
    if direct_url.strip():
        post_type = detect_post_type(direct_url)
        caption = generate_caption(style, content_mode)
        try:
            if post_type == "reel":
                send_message_to_telegram(f"🎬 Reel\n\n{direct_url}\n\n{caption}")
                st.success("Reel sent to Telegram.")
            elif post_type == "photo":
                paths = download_photo_post(direct_url)
                count = send_carousel_to_telegram(paths, caption, direct_url)
                st.success(f"{count} photo(s) sent.")
            else:
                st.warning("Unknown URL type.")
        except Exception as e:
            st.error(str(e))
    else:
        st.warning("Enter a URL first.")

st.markdown("---")

# ── CAPTION GENERATOR ──
st.markdown("## ✍️ AI Caption Generator")
c1, c2 = st.columns([2, 1])
with c1:
    cap_topic = st.text_input("Topic", placeholder="e.g. airport look, red dress photoshoot")
with c2:
    cap_style = st.selectbox("Caption Style", ["Dreamy", "Main Character", "Trending"], key="cap_style")

if st.button("✨ Generate 5 Captions"):
    if cap_topic.strip():
        with st.spinner("Generating..."):
            variants = generate_caption_variants(cap_topic, cap_style)
        for i, cap in enumerate(variants, 1):
            st.markdown(f"""
            <div class='card' style='padding:14px 18px;display:flex;align-items:center;gap:12px;'>
                <span style='background:linear-gradient(135deg,#ff6fab,#e8006e);color:white;
                      border-radius:50%;width:28px;height:28px;display:flex;align-items:center;
                      justify-content:center;font-weight:700;font-size:13px;flex-shrink:0;'>{i}</span>
                <span>{cap}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Enter a topic first.")

st.markdown("---")

# ── HASHTAG PACK ──
st.markdown("## #️⃣ Hashtag Pack Generator")
h1, h2 = st.columns([2, 1])
with h1:
    hash_topic = st.text_input("Topic", placeholder="e.g. Gayatri Bhardwaj fashion", key="hash_topic")
with h2:
    hash_niche = st.selectbox("Niche", ["actress fanpage", "fashion", "aesthetic", "bollywood"])

if st.button("🔥 Generate Hashtag Pack"):
    if hash_topic.strip():
        with st.spinner("Building hashtag pack..."):
            pack = generate_hashtag_pack(hash_topic, hash_niche)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🔴 Mega (10M+)**")
            st.code(" ".join(pack.get("mega", [])), language=None)
        with col2:
            st.markdown("**🟡 Mid (500K–5M)**")
            st.code(" ".join(pack.get("mid", [])), language=None)
        with col3:
            st.markdown("**🟢 Niche (<500K)**")
            st.code(" ".join(pack.get("niche", [])), language=None)
        all_tags = " ".join(pack.get("mega", []) + pack.get("mid", []) + pack.get("niche", []))
        st.download_button("📋 Download All Hashtags", data=all_tags, file_name="hashtags.txt")
    else:
        st.warning("Enter a topic first.")
