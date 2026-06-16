import os
import json
import math
import tempfile
import pandas as pd
import streamlit as st
from PIL import Image
from core_engine import (
    init_db, migrate_db, clean_handles, get_posts,
    sync_data, clear_old_data, process_post,
    deep_search_and_send, smart_discovery_ai, deep_discovery_ai,
    detect_post_type, generate_caption, extract_shortcode,
    send_message_to_telegram, download_photo_post, send_carousel_to_telegram,
    generate_caption_variants, generate_hashtag_pack,
    get_best_posting_times, add_watermark, get_content_log,
    make_collage, apply_style_filter, ai_style_edit,
    STYLE_PRESETS, costume_transfer
)
from theme import THEME_CSS, HERO_HTML

st.set_page_config(page_title="Gayu_theHelper", page_icon="🌸", layout="wide", initial_sidebar_state="collapsed")
init_db()
migrate_db()
st.markdown(THEME_CSS, unsafe_allow_html=True)
st.markdown(HERO_HTML, unsafe_allow_html=True)

# ── TOP NAV ──
NAV = {
    "dashboard":  "🏠 Dashboard",
    "discovery":  "🔍 Discovery",
    "import":     "📦 Import JSON",
    "captions":   "✍️ Captions",
    "creative":   "🎨 Creative",
    "analytics":  "📊 Analytics",
}
page = st.query_params.get("page", "dashboard")

nav_html = '<div class="nav-menu">'
for key, label in NAV.items():
    active = "active" if page == key else ""
    nav_html += f'<a class="nav-btn {active}" href="?page={key}">{label}</a>'
nav_html += "</div>"
st.markdown(nav_html, unsafe_allow_html=True)
st.markdown("---")

# ══════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════
if page == "dashboard":
    handles_input = st.text_input("Instagram Handle", value="@gayatribhardwaj__")
    handles = clean_handles(handles_input)
    posts = get_posts(handles)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✨ Total Posts", len(posts))
    c2.metric("🔥 Viral Picks", sum(1 for p in posts if p[7] >= 80))
    c3.metric("💬 Active", len([p for p in posts if p[6] != "SKIPPED"]))
    c4.metric("⏭ Skipped", len([p for p in posts if p[6] == "SKIPPED"]))

    st.markdown("### 💖 Suggested Content")
    if not posts:
        st.info("No posts found. Go to 🔍 Discovery to sync data first.")
    else:
        style = st.selectbox("Caption Style", ["Dreamy", "Main Character", "Trending"], key="dash_style")
        for row in posts[:10]:
            post_id, handle, shortcode, url, post_type, saved_mode, status, viral_score, engagement_rating, category, reason, gemini_caption = row
            score_color = "#e8006e" if viral_score >= 80 else "#f4a261" if viral_score >= 60 else "#8d99ae"
            st.markdown(f"""
            <div class='card'>
                <b style='color:#e8006e;'>@{handle}</b> &nbsp;·&nbsp; {post_type} &nbsp;·&nbsp;
                <b style='color:{score_color};'>{viral_score}/100</b> &nbsp;·&nbsp; {engagement_rating}<br>
                <small style='color:#888;'>{reason}</small>
                <div style='background:rgba(255,240,248,0.9);padding:12px;border-radius:12px;margin-top:8px;font-style:italic;'>
                    ✨ {gemini_caption}
                </div>
                <small style='color:#aaa;'>🔗 {url}</small>
            </div>
            """, unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("✨ Send to Telegram", key=f"send_{post_id}"):
                    result = process_post(post_id, handle, shortcode, url, post_type, saved_mode, style)
                    st.success(result)
            with b2:
                if st.button("🗑 Hide", key=f"hide_{post_id}"):
                    st.toast(f"Hidden {shortcode}")

# ══════════════════════════════════════════
# 🔍 DISCOVERY
# ══════════════════════════════════════════
elif page == "discovery":
    st.markdown("## 🔍 Content Discovery")
    handles_input = st.text_input("Handles (one per line)", value="@gayatribhardwaj__", key="disc_handles")
    handles = clean_handles(handles_input)
    col1, col2 = st.columns(2)
    with col1:
        content_mode = st.selectbox("Content Mode", ["Photo Posts", "Solo Pics Only", "High Engagement Photos", "Reels Only"])
    with col2:
        deep_mode = st.selectbox("Deep Search Mode", ["Hidden Gems", "Photoshoots", "Candid Looks", "Event Looks", "High Reach Looks"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Sync")
        if st.button("🔄 Sync Data", key="sync_btn"):
            with st.spinner("Syncing..."):
                try:
                    count = sync_data(handles, content_mode)
                    st.success(f"Synced {count} posts!")
                except Exception as e:
                    st.error(str(e))
        if st.button("🗑 Clear All Data", key="clear_btn"):
            clear_old_data(); st.success("Cleared.")

    with c2:
        st.markdown("#### Deep Search")
        deep_limit = st.slider("Photos to find", 5, 30, 10, 5)
        if st.button("🔎 Deep Search & Send", key="deep_btn"):
            with st.spinner("Searching..."):
                try:
                    result = deep_search_and_send(handles=handles, deep_mode=deep_mode, limit=deep_limit)
                    st.success(result)
                except Exception as e:
                    st.error(str(e))

    with c3:
        st.markdown("#### Smart AI")
        smart_limit = st.select_slider("AI Limit", options=[3, 5, 10], value=5)
        if st.button("🚀 Smart Discovery", key="smart_btn"):
            with st.spinner("Running AI..."):
                try:
                    mode_slug = deep_mode.lower().replace(" ", "_")
                    result = smart_discovery_ai(handles=handles, deep_mode=mode_slug, limit=smart_limit)
                    st.success(result)
                except Exception as e:
                    st.error(str(e))

    st.markdown("---")
    st.markdown("### 🌌 Deep Discovery AI")
    disc_handles = st.text_area("Discovery Handles", value="@gayatribhardwaj__", key="disc_handles2")
    prompt_file = st.file_uploader("Custom prompt .txt (optional)", type=["txt"])
    custom_p = None
    if prompt_file:
        try: custom_p = prompt_file.read().decode("utf-8")
        except Exception: pass
    if st.button("🚀 Start Deep Discovery AI", key="deep_ai_btn"):
        with st.spinner("Running..."):
            try:
                mode_slug = deep_mode.lower().replace(" ", "_")
                result = deep_discovery_ai(handles=clean_handles(disc_handles), deep_mode=mode_slug, limit=10, custom_prompt=custom_p)
                st.success(result)
            except Exception as e:
                st.error(str(e))

# ══════════════════════════════════════════
# 📦 IMPORT JSON
# ══════════════════════════════════════════
elif page == "import":
    st.markdown("## 📦 Import Scraped JSON")
    col1, col2 = st.columns(2)
    with col1:
        style = st.selectbox("Caption Style", ["Dreamy", "Main Character", "Trending"], key="imp_style")
    with col2:
        content_mode = st.selectbox("Content Mode", ["Photo Posts", "Solo Pics Only", "High Engagement Photos", "Reels Only"], key="imp_mode")

    uploaded_json = st.file_uploader("Upload scraped JSON", type=["json"])

    def clean_json_posts(data):
        if not isinstance(data, list): data = [data]
        unique_posts, seen = [], set()
        for item in data:
            if not isinstance(item, dict): continue
            url = (item.get("url") or item.get("post_url") or item.get("link")
                   or item.get("instagramUrl") or item.get("shortCodeUrl"))
            if not url: continue
            url = url.split("?")[0].strip()
            key = extract_shortcode(url) or url
            if key in seen: continue
            seen.add(key); item["_clean_url"] = url; unique_posts.append(item)
        return unique_posts

    if uploaded_json:
        try:
            data = json.load(uploaded_json)
            total_items = len(data) if isinstance(data, list) else 1
            st.success(f"✨ Loaded {total_items} items")
            c1, c2, c3 = st.columns(3)
            c1.metric("Posts Found", total_items)
            c2.metric("Type", "Instagram")
            c3.metric("Ready", "✅")
            with st.expander("Preview first item"):
                st.write(data[0] if isinstance(data, list) else data)
            cleaned = clean_json_posts(data)
            num_batches = math.ceil(len(cleaned) / 10)
            st.markdown(f"### 🚀 {len(cleaned)} posts · {num_batches} batches")
            for i in range(0, num_batches, 5):
                cols = st.columns(5)
                for j in range(5):
                    idx = i + j
                    if idx >= num_batches: break
                    s, e = idx * 10, min((idx + 1) * 10, len(cleaned))
                    if cols[j].button(f"Batch {idx+1}", key=f"batch_{idx}"):
                        prog = st.progress(0); ok = fail = 0
                        for n, item in enumerate(cleaned[s:e]):
                            try:
                                url = item["_clean_url"]
                                pt = detect_post_type(url)
                                cap = generate_caption(style, content_mode)
                                if pt == "photo":
                                    paths = download_photo_post(url)
                                    send_carousel_to_telegram(paths, cap, url)
                                elif pt == "reel":
                                    send_message_to_telegram(f"🎬 Reel\n\n{url}\n\n{cap}")
                                ok += 1
                            except Exception as ex:
                                fail += 1; st.error(str(ex))
                            prog.progress((n+1)/(e-s))
                        st.success(f"Batch {idx+1}: ✅ {ok} sent, ❌ {fail} failed")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

# ══════════════════════════════════════════
# ✍️ CAPTIONS
# ══════════════════════════════════════════
elif page == "captions":
    st.markdown("## 🔗 Quick URL Fetch")
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        direct_url = st.text_input("Instagram Post/Reel URL", placeholder="https://www.instagram.com/p/XXXXX/")
    with col2:
        style = st.selectbox("Style", ["Dreamy", "Main Character", "Trending"], key="cap_url_style")
    with col3:
        content_mode = st.selectbox("Mode", ["Photo Posts", "Solo Pics Only", "High Engagement Photos", "Reels Only"], key="cap_url_mode")
    if st.button("✨ Fetch & Send", key="fetch_send"):
        if direct_url.strip():
            pt = detect_post_type(direct_url)
            cap = generate_caption(style, content_mode)
            try:
                if pt == "reel":
                    send_message_to_telegram(f"🎬 Reel\n\n{direct_url}\n\n{cap}"); st.success("Sent!")
                elif pt == "photo":
                    paths = download_photo_post(direct_url)
                    st.success(f"{send_carousel_to_telegram(paths, cap, direct_url)} photo(s) sent.")
                else:
                    st.warning("Unknown URL type.")
            except Exception as e:
                st.error(str(e))

    st.markdown("---")
    st.markdown("## ✍️ AI Caption Generator")
    c1, c2 = st.columns([2, 1])
    with c1:
        cap_topic = st.text_input("Topic", placeholder="e.g. airport look, red dress photoshoot")
    with c2:
        cap_style = st.selectbox("Style", ["Dreamy", "Main Character", "Trending"], key="cap_style")
    if st.button("✨ Generate 5 Captions", key="gen_caps"):
        if cap_topic.strip():
            with st.spinner("Generating..."):
                variants = generate_caption_variants(cap_topic, cap_style)
            for i, cap in enumerate(variants, 1):
                st.markdown(f"""
                <div class='card' style='padding:14px 18px;display:flex;align-items:center;gap:12px;'>
                    <span style='background:linear-gradient(135deg,#ff6fab,#e8006e);color:white;border-radius:50%;
                          width:28px;height:28px;display:flex;align-items:center;justify-content:center;
                          font-weight:700;font-size:13px;flex-shrink:0;'>{i}</span>
                    <span>{cap}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Enter a topic first.")

    st.markdown("---")
    st.markdown("## #️⃣ Hashtag Pack Generator")
    h1, h2 = st.columns([2, 1])
    with h1:
        hash_topic = st.text_input("Topic", placeholder="e.g. Gayatri Bhardwaj fashion", key="hash_topic")
    with h2:
        hash_niche = st.selectbox("Niche", ["actress fanpage", "fashion", "aesthetic", "bollywood"])
    if st.button("🔥 Generate Hashtag Pack", key="gen_hash"):
        if hash_topic.strip():
            with st.spinner("Building..."):
                pack = generate_hashtag_pack(hash_topic, hash_niche)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**🔴 Mega**"); st.code(" ".join(pack.get("mega", [])), language=None)
            with col2:
                st.markdown("**🟡 Mid**"); st.code(" ".join(pack.get("mid", [])), language=None)
            with col3:
                st.markdown("**🟢 Niche**"); st.code(" ".join(pack.get("niche", [])), language=None)
            all_tags = " ".join(pack.get("mega",[]) + pack.get("mid",[]) + pack.get("niche",[]))
            st.download_button("📋 Download Hashtags", data=all_tags, file_name="hashtags.txt", key="dl_hash")
        else:
            st.warning("Enter a topic first.")

# ══════════════════════════════════════════
# 🎨 CREATIVE
# ══════════════════════════════════════════
elif page == "creative":
    st.markdown("## 🎨 Creative Tools")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🖊️ Watermark", "🖼️ Collage", "🎬 Style Filter", "🤖 AI Edit", "👗 Costume Transfer"])

    with tab1:
        st.markdown("### 🖊️ Watermark Tool")
        wm_text = st.text_input("Watermark Text", value="@gayatribhardwaj__")
        wm_file = st.file_uploader("Upload Image", type=["jpg","jpeg","png"], key="wm_up")
        if st.button("💧 Apply Watermark", key="wm_btn"):
            if wm_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
                    t.write(wm_file.read()); tmp = t.name
                try:
                    out = add_watermark(tmp, wm_text)
                    c1, c2 = st.columns(2)
                    c1.image(Image.open(tmp), caption="Original", use_container_width=True)
                    c2.image(Image.open(out), caption="Watermarked", use_container_width=True)
                    with open(out, "rb") as f:
                        st.download_button("⬇️ Download", data=f, file_name="watermarked.jpg", key="dl_wm")
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Upload an image first.")

    with tab2:
        st.markdown("### 🖼️ Photo Collage Maker")
        collage_files = st.file_uploader("Upload 2–6 photos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="collage_up")
        c1, c2 = st.columns(2)
        layout = c1.selectbox("Layout", ["2x2","3x1","1x3","2x3","3x2"])
        title_text = c2.text_input("Title (optional)", value="@gayatribhardwaj__")
        if st.button("✨ Create Collage", key="collage_btn"):
            if collage_files:
                tmp_paths = []
                for f in collage_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
                        t.write(f.read()); tmp_paths.append(t.name)
                try:
                    out = make_collage(tmp_paths, layout=layout, title_text=title_text)
                    st.image(Image.open(out), caption="Collage", use_container_width=True)
                    with open(out, "rb") as f:
                        st.download_button("⬇️ Download Collage", data=f, file_name="collage.jpg", key="dl_collage")
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Upload at least 2 photos.")

    with tab3:
        st.markdown("### 🎬 Cinematic Style Filter")
        filter_file = st.file_uploader("Upload photo", type=["jpg","jpeg","png"], key="filter_up")
        preset = st.selectbox("Preset", list(STYLE_PRESETS.keys()))
        if st.button("🎨 Apply Filter", key="filter_btn"):
            if filter_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
                    t.write(filter_file.read()); tmp = t.name
                try:
                    out = apply_style_filter(tmp, preset)
                    c1, c2 = st.columns(2)
                    c1.image(Image.open(tmp), caption="Original", use_container_width=True)
                    c2.image(Image.open(out), caption=preset, use_container_width=True)
                    with open(out, "rb") as f:
                        st.download_button("⬇️ Download", data=f, file_name="styled.jpg", key="dl_filter")
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Upload a photo first.")

    with tab4:
        st.markdown("### 🤖 AI Style Edit")
        st.caption("Free tier: 25 credits/month · platform.stability.ai · Falls back to local filter if no key")
        ai_file = st.file_uploader("Upload photo", type=["jpg","jpeg","png"], key="ai_up")
        ai_presets = {
            "Cinematic Edit": "cinematic film still, dramatic lighting, 8k, highly detailed",
            "Saree Look": "wearing elegant silk saree, traditional Indian outfit, golden border, soft studio lighting",
            "Western Dress": "wearing stylish western dress, fashion editorial, clean background",
            "Royal Look": "wearing royal Indian lehenga, jewellery, regal pose, bokeh background",
            "Street Style": "wearing trendy street fashion, urban background, candid natural light",
            "Custom": ""
        }
        choice = st.selectbox("Style", list(ai_presets.keys()), key="ai_preset")
        prompt = ai_presets[choice]
        if choice == "Custom":
            prompt = st.text_area("Custom prompt", placeholder="cinematic lighting, golden hour...")
        strength = st.slider("Edit Strength", 0.3, 0.9, 0.6, 0.05, key="ai_str")
        if st.button("🚀 Generate AI Edit", key="ai_btn"):
            if ai_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
                    t.write(ai_file.read()); tmp = t.name
                with st.spinner("Generating..."):
                    try:
                        out, msg = ai_style_edit(tmp, prompt, strength=strength)
                        st.info(msg)
                        c1, c2 = st.columns(2)
                        c1.image(Image.open(tmp), caption="Original", use_container_width=True)
                        c2.image(Image.open(out), caption="AI Edit", use_container_width=True)
                        with open(out, "rb") as f:
                            st.download_button("⬇️ Download", data=f, file_name="ai_edit.jpg", key="dl_ai")
                    except Exception as e:
                        st.error(str(e))
            else:
                st.warning("Upload a photo first.")

    with tab5:
        st.markdown("### 👗 Costume Transfer")
        st.caption("Gemini reads reference costume → Stability AI applies it to person photo")
        c1, c2 = st.columns(2)
        with c1:
            person_file = st.file_uploader("Person Photo", type=["jpg","jpeg","png"], key="ct_person")
            if person_file: st.image(person_file, use_container_width=True)
        with c2:
            costume_file = st.file_uploader("Reference Costume", type=["jpg","jpeg","png"], key="ct_costume")
            if costume_file: st.image(costume_file, use_container_width=True)
        ct_str = st.slider("Transfer Strength", 0.4, 0.9, 0.7, 0.05, key="ct_str")
        if st.button("👗 Apply Costume Transfer", key="ct_btn"):
            if person_file and costume_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tp:
                    tp.write(person_file.read()); p_tmp = tp.name
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tc:
                    tc.write(costume_file.read()); c_tmp = tc.name
                with st.spinner("Processing..."):
                    try:
                        out, msg = costume_transfer(p_tmp, c_tmp, strength=ct_str)
                        st.success(msg)
                        st.image(Image.open(out), caption="Result", use_container_width=True)
                        with open(out, "rb") as f:
                            st.download_button("⬇️ Download", data=f, file_name="costume_result.jpg", key="dl_ct")
                    except Exception as e:
                        st.error(str(e))
            else:
                st.warning("Upload both photos first.")

# ══════════════════════════════════════════
# 📊 ANALYTICS
# ══════════════════════════════════════════
elif page == "analytics":
    st.markdown("## 📊 Analytics & Planning")
    st.markdown("### 🕐 Best Posting Times")
    times = get_best_posting_times()
    time_df = pd.DataFrame(times)
    st.dataframe(time_df, use_container_width=True, hide_index=True)
    st.download_button("📅 Download Schedule", data=time_df.to_csv(index=False), file_name="schedule.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("### 📅 Content Sent Log")
    log_rows = get_content_log()
    if not log_rows:
        st.info("No sent posts yet.")
    else:
        log_df = pd.DataFrame(log_rows, columns=["Handle","Shortcode","URL","Type","Status","Viral Score","Caption","Sent At"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Sent", len(log_df))
        c2.metric("Photos", len(log_df[log_df["Type"]=="photo"]))
        c3.metric("Reels", len(log_df[log_df["Type"]=="reel"]))
        c4.metric("Avg Score", round(log_df["Viral Score"].mean(), 1))
        st.dataframe(log_df[["Handle","Type","Status","Viral Score","Caption","Sent At"]], use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export CSV", data=log_df.to_csv(index=False), file_name="content_log.csv", mime="text/csv")
