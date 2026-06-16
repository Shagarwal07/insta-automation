import os
import json
import math
import pandas as pd
import streamlit as st
from PIL import Image
from core_engine import (
    init_db, migrate_db, clear_old_data, clean_handles, sync_data, get_posts,
    process_post, detect_post_type, generate_caption,
    send_message_to_telegram, download_photo_post, send_photo_to_telegram,
    send_carousel_to_telegram, deep_search_and_send, deep_discovery_ai,
    smart_discovery_ai, extract_shortcode,
    generate_caption_variants, generate_hashtag_pack,
    get_best_posting_times, add_watermark, get_content_log,
    make_collage, apply_style_filter, ai_style_edit, STYLE_PRESETS
)

# Initialize DB on app start
init_db()
migrate_db()

st.set_page_config(
    page_title="Gayu_theHelper",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================
# BABY PINK UI THEME
# =========================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, .stApp, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

/* Main background */
.stApp {
    background: #fff5f8;
    color: #3b1f2b !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #ffd9e7 !important;
    border-right: 2px solid #f7a8c4;
}

section[data-testid="stSidebar"] * {
    color: #3b1f2b !important;
}

/* Main text */
h1, h2, h3, h4, p, label, span, div {
    color: #3b1f2b !important;
}

/* Hero */
.hero {
    background: #fffafd;
    border: 1px solid #ffc2d6;
    border-radius: 28px;
    padding: 40px;
    text-align: center;
    box-shadow: 0 10px 35px rgba(255, 143, 171, 0.18);
    margin-bottom: 35px;
}

.mainTitle {
    color: #d63384 !important;
    font-size: 58px;
    font-weight: 700;
}

.subTitle {
    color: #9d4b6c !important;
    font-size: 18px;
}

/* Inputs */
input, textarea {
    background: #ffffff !important;
    color: #3b1f2b !important;
    border: 1.5px solid #f7a8c4 !important;
    border-radius: 14px !important;
}

input::placeholder,
textarea::placeholder {
    color: #9d7b87 !important;
}

/* Selectbox */
div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #3b1f2b !important;
    border: 1.5px solid #f7a8c4 !important;
    border-radius: 14px !important;
}

div[data-baseweb="select"] span {
    color: #3b1f2b !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #ff7eb3, #ff9fba) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 600 !important;
    padding: 0.7rem 1.2rem !important;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #f85f9d, #ff89aa) !important;
    box-shadow: 0 8px 20px rgba(255, 105, 180, 0.25);
}

/* Cards */
.card {
    background: white;
    border: 1px solid #ffc2d6;
    border-radius: 22px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(255, 143, 171, 0.14);
}

/* Metrics */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #ffc2d6;
    border-radius: 18px;
    padding: 14px;
}

/* Remove dark top header */
header {
    background: #fff5f8 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div style="font-size:52px;">🌸</div>
    <div class="mainTitle">Gayu_theHelper</div>
    <div class="subTitle">Your Dreamy Content Companion ✨</div>
</div>
""", unsafe_allow_html=True)

# =========================================
# SIDEBAR
# =========================================

st.sidebar.title("🌷 Control Panel")

handles_input = st.sidebar.text_area(
    "Instagram Handles",
    value="@gayatribhardwaj__",
    height=120
)

content_mode = st.sidebar.selectbox(
    "Content Mode",
    ["Photo Posts", "Solo Pics Only", "High Engagement Photos", "Reels Only"]
)

style = st.sidebar.selectbox(
    "Caption Style",
    ["Dreamy", "Main Character", "Trending"]
)

if st.sidebar.button("Clear Old Data"):
    clear_old_data()
    st.sidebar.success("Old data cleared.")

if st.sidebar.button("Sync Data"):
    handles = clean_handles(handles_input)
    sync_data(handles, content_mode)
    st.sidebar.success("Sync completed.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Deep Search")

deep_mode = st.sidebar.selectbox(
    "Deep Search Mode",
    [
        "Hidden Gems",
        "Photoshoots",
        "Candid Looks",
        "Event Looks",
        "High Reach Looks"
    ]
)

deep_limit = st.sidebar.slider(
    "Photos to Send",
    min_value=5,
    max_value=30,
    value=10,
    step=5
)

if st.sidebar.button("🔎 Deep Search & Send"):
    handles = clean_handles(handles_input)
    result = deep_search_and_send(
        handles=handles,
        deep_mode=deep_mode,
        limit=deep_limit
    )
    st.sidebar.success(result)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 Smart Discovery (AI + CV)")
smart_limit = st.sidebar.select_slider("AI Analysis Limit", options=[3, 5, 10], value=5)

if st.sidebar.button("🚀 Run Smart Discovery"):
    handles = clean_handles(handles_input)
    # Normalize deep_mode to snake_case for the engine
    mode_slug = deep_mode.lower().replace(" ", "_")
    
    with st.spinner("Filtering locally & Analyzing with AI..."):
        result = smart_discovery_ai(
            handles=handles,
            deep_mode=mode_slug,
            limit=smart_limit,
            discovery_engine="google_images"
        )
    st.sidebar.success(result)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌌 Deep Discovery AI")
discovery_handles = st.sidebar.text_area("Discovery Handles", value="@gayatribhardwaj__", key="discovery_handles")
prompt_file = st.sidebar.file_uploader("Upload discovery prompt (optional)", type=["txt"])

if st.sidebar.button("🚀 Start Deep Discovery AI"):
    handles = clean_handles(discovery_handles)
    custom_p = None
    if prompt_file:
        try:
            custom_p = prompt_file.read().decode("utf-8")
        except:
            st.sidebar.error("Could not read prompt file.")
    
    with st.spinner("Executing Deep Discovery AI..."):
        mode_slug = deep_mode.lower().replace(" ", "_")
        result = deep_discovery_ai(
            handles=handles,
            deep_mode=mode_slug,
            limit=10,
            custom_prompt=custom_p,
            discovery_engine="google_images"
        )
    st.sidebar.success(result)

# =========================================
# DIRECT URL INPUT
# =========================================

st.markdown("## 🔗 Quick URL Fetch")

direct_url = st.text_input(
    "Paste Instagram Post/Reel URL",
    placeholder="https://www.instagram.com/p/XXXXX/"
)

if st.button("✨ Fetch & Send"):
    if direct_url.strip():
        post_type = detect_post_type(direct_url)
        caption = generate_caption(style, content_mode)
        try:
            if post_type == "reel":
                message = f"🎬 Reel Found\n\nLink:\n{direct_url}\n\nCaption:\n{caption}"
                send_message_to_telegram(message)
                st.success("Reel link sent to Telegram.")
            elif post_type == "photo":
                image_paths = download_photo_post(direct_url)
                sent_count = send_carousel_to_telegram(
                    image_paths=image_paths,
                    caption=caption,
                    source_url=direct_url
                )
                st.success(f"{sent_count} photo(s) downloaded & sent.")
            else:
                st.warning("Unknown Instagram URL type.")
        except Exception as e:
            st.error(str(e))

# =========================================
# SMART JSON IMPORT
# =========================================

st.markdown("## 📦 Import Scraped JSON")

uploaded_json = st.file_uploader(
    "Upload Instagram scraped JSON",
    type=["json"]
)

if uploaded_json:

    try:

        data = json.load(uploaded_json)

        # -------------------------
        # JSON CLEANER + DEDUP
        # -------------------------

        def clean_json_posts(data):
            if not isinstance(data, list):
                data = [data]

            unique_posts = []
            seen = set()

            for item in data:
                if not isinstance(item, dict):
                    continue

                url = (
                    item.get("url")
                    or item.get("post_url")
                    or item.get("link")
                    or item.get("instagramUrl")
                    or item.get("shortCodeUrl")
                )

                if not url:
                    continue

                # normalize URL
                url = url.split("?")[0].strip()
                shortcode = extract_shortcode(url)
                unique_key = shortcode or url

                if unique_key in seen:
                    continue

                seen.add(unique_key)
                item["_clean_url"] = url
                unique_posts.append(item)

            return unique_posts

        st.success("✨ JSON loaded successfully")

        # ---------------------------
        # Show summary instead of full JSON
        # ---------------------------

        total_items = len(data) if isinstance(data, list) else 1

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Posts Found", total_items)

        with col2:
            st.metric("Detected Type", "Instagram")

        with col3:
            st.metric("Ready", "Yes")

        with st.expander("Preview First Item"):
            if isinstance(data, list):
                st.write(data[0])
            else:
                st.write(data)

        # ---------------------------
        # Process Button
        # ---------------------------

        cleaned_posts = clean_json_posts(data) # This function is defined within app.py
        batch_size = 10
        total_posts = len(cleaned_posts)
        num_batches = math.ceil(total_posts / batch_size)

        st.markdown(f"### 🚀 Batch Processing ({batch_size} items per click)")
        
        # Create a grid of buttons for batches
        for i in range(0, num_batches, 5):
            btn_cols = st.columns(5)
            for j in range(5):
                batch_idx = i + j
                if batch_idx < num_batches:
                    start_idx = batch_idx * batch_size
                    end_idx = min((batch_idx + 1) * batch_size, total_posts)
                    
                    if btn_cols[j].button(f"Batch {batch_idx + 1}", help=f"Process items {start_idx+1}-{end_idx}", key=f"batch_btn_{batch_idx}"):
                        processed = 0
                        failed = 0
                        batch_to_process = cleaned_posts[start_idx:end_idx]
                        
                        progress = st.progress(0)
                        for idx, item in enumerate(batch_to_process):
                            try:
                                url = item["_clean_url"]
                                post_type = detect_post_type(url)
                                
                                # Fallback caption if processing directly from JSON without DB sync
                                caption = generate_caption(style, content_mode)

                                if post_type == "photo":
                                    image_paths = download_photo_post(url)
                                    send_carousel_to_telegram(image_paths, caption, url)
                                elif post_type == "reel":
                                    message = f"🎬 Reel Found\n\nLink:\n{url}\n\nCaption:\n{caption}"
                                    send_message_to_telegram(message) # This will use the caption from the DB
                                
                                processed += 1
                            except Exception as e:
                                failed += 1
                                st.error(f"Error on {url}: {e}")
                            
                            progress.progress((idx + 1) / len(batch_to_process))
                        
                        st.success(f"Batch {batch_idx + 1} Finished! Processed: {processed}, Failed: {failed}")

    except Exception as e:
        st.error(f"Invalid JSON file: {str(e)}")

# =========================================
# BEAUTIFUL METRICS
# =========================================

st.markdown("## 📊 Content Overview")
col1, col2, col3, col4 = st.columns(4)

handles = clean_handles(handles_input) # Ensure handles are cleaned for get_posts
posts = get_posts(handles) # Fetch posts here to get accurate counts

with col1: st.metric("✨ Total Posts", len(posts))
with col2: st.metric("🔥 Viral Picks", sum(1 for p in posts if p[7] >= 80)) # Assuming viral_score is at index 7
with col3: st.metric("💬 Avg Engagement", "High") # Placeholder, could be calculated from DB
with col4: st.metric("🌸 Dreamy Score", "91%") # Placeholder

# =========================================
# SUGGESTED CONTENT
# =========================================

st.markdown("## 💖 Suggested Content")

if not posts:
    st.info("No posts found. Click Sync Data first.")
else:
    for row in posts:
        (
            post_id, handle, shortcode, url, post_type, saved_mode, status, # Existing fields
            viral_score, engagement_rating, category, reason, gemini_caption
        ) = row
        
        score_color = (
            "#ff4d6d"
            if viral_score >= 80
            else "#f4a261"
            if viral_score >= 60
            else "#8d99ae"
        )

        st.markdown(f"""
        <div class='card'>
            <h2>🌸 @{handle}</h2>
            <p>📷 <b>Type:</b> {post_type} | 🏷 <b>Category:</b> {category}</p>
            <p>🔥 <b style='color:{score_color};'>{viral_score}/100</b> | 💬 {engagement_rating}</p>
            <p>📝 {reason}</p>
            <div style='background:#fff0f6; padding:15px; border-radius:12px; margin-top:10px;'>
                ✨ {gemini_caption}
            </div>
            <br>
            🔗 {url}
        </div>
        """, unsafe_allow_html=True)

        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("✨ Send", key=f"s_{post_id}"):
                result = process_post(post_id, handle, shortcode, url, post_type, saved_mode, style)
                st.success(result)
        
        with btn_col2:
            if st.button("💖 Favorite", key=f"fav_{post_id}"):
                st.toast(f"Added {shortcode} to favorites!")
        
        with btn_col3:
            if st.button("🗑 Remove", key=f"remove_{post_id}"):
                st.toast(f"Hidden {shortcode}")

        st.markdown("<br>", unsafe_allow_html=True)

# =========================================
# IMAGE PREVIEW
# =========================================

st.markdown("## 🖼 Latest Downloaded")

downloads_folders = [
    "downloads/photos",
    "downloads/deep_images"
]

image_files = []

for folder in downloads_folders:
    if os.path.exists(folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    image_files.append(os.path.join(root, file))

image_files = sorted(
    image_files,
    key=os.path.getmtime,
    reverse=True
)

image_files = image_files[:9]

if image_files:
    cols = st.columns(3)
    for i, image_path in enumerate(image_files):
        with cols[i % 3]:
            try:
                image = Image.open(image_path)
                st.image(image, use_container_width=True)
            except: pass

# =========================================
# FEATURE: AI CAPTION GENERATOR
# =========================================

st.markdown("---")
st.markdown("## ✍️ AI Caption Generator")

cap_col1, cap_col2 = st.columns([2, 1])
with cap_col1:
    cap_topic = st.text_input("Caption Topic", placeholder="e.g. airport look, red dress photoshoot")
with cap_col2:
    cap_style = st.selectbox("Style", ["Dreamy", "Main Character", "Trending"], key="cap_style")

if st.button("✨ Generate 5 Captions"):
    if cap_topic.strip():
        with st.spinner("Generating captions..."):
            variants = generate_caption_variants(cap_topic, cap_style)
        for i, cap in enumerate(variants, 1):
            st.markdown(f"""
            <div class='card' style='padding:14px;'>
                <b>#{i}</b> &nbsp; {cap}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Enter a topic first.")

# =========================================
# FEATURE: HASHTAG PACK GENERATOR
# =========================================

st.markdown("---")
st.markdown("## #️⃣ Hashtag Pack Generator")

hash_col1, hash_col2 = st.columns([2, 1])
with hash_col1:
    hash_topic = st.text_input("Hashtag Topic", placeholder="e.g. Gayatri Bhardwaj fashion")
with hash_col2:
    hash_niche = st.selectbox("Niche", ["actress fanpage", "fashion", "aesthetic", "bollywood"])

if st.button("🔥 Generate Hashtag Pack"):
    if hash_topic.strip():
        with st.spinner("Building hashtag pack..."):
            pack = generate_hashtag_pack(hash_topic, hash_niche)
        h1, h2, h3 = st.columns(3)
        with h1:
            st.markdown("**🔴 Mega (10M+)**")
            st.code(" ".join(pack.get("mega", [])), language=None)
        with h2:
            st.markdown("**🟡 Mid (500K-5M)**")
            st.code(" ".join(pack.get("mid", [])), language=None)
        with h3:
            st.markdown("**🟢 Niche (<500K)**")
            st.code(" ".join(pack.get("niche", [])), language=None)

        all_tags = " ".join(pack.get("mega", []) + pack.get("mid", []) + pack.get("niche", []))
        st.download_button("📋 Copy All Hashtags", data=all_tags, file_name="hashtags.txt")
    else:
        st.warning("Enter a topic first.")

# =========================================
# FEATURE: WATERMARK TOOL
# =========================================

st.markdown("---")
st.markdown("## 🖊️ Watermark Tool")

wm_col1, wm_col2 = st.columns([2, 1])
with wm_col1:
    wm_text = st.text_input("Watermark Text", value="@gayatribhardwaj__")
with wm_col2:
    wm_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"], key="wm_upload")

if st.button("💧 Apply Watermark") and wm_file:
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(wm_file.read())
        tmp_path = tmp.name
    try:
        out_path = add_watermark(tmp_path, wm_text)
        wm_img = Image.open(out_path)
        st.image(wm_img, caption="Watermarked Preview", use_container_width=True)
        with open(out_path, "rb") as f:
            st.download_button("⬇️ Download Watermarked Image", data=f, file_name="watermarked.jpg")
    except Exception as e:
        st.error(f"Watermark failed: {e}")

# =========================================
# FEATURE: BEST POSTING TIMES
# =========================================

st.markdown("---")
st.markdown("## 🕐 Best Posting Times")

times = get_best_posting_times()
time_df = pd.DataFrame(times)
st.dataframe(time_df, use_container_width=True, hide_index=True)
st.download_button(
    "📅 Download Schedule CSV",
    data=time_df.to_csv(index=False),
    file_name="posting_schedule.csv",
    mime="text/csv"
)

# =========================================
# FEATURE: CONTENT CALENDAR / LOG
# =========================================

st.markdown("---")
st.markdown("## 📅 Content Log")

log_rows = get_content_log()
if not log_rows:
    st.info("No sent posts yet. Send some content first.")
else:
    log_df = pd.DataFrame(log_rows, columns=[
        "Handle", "Shortcode", "URL", "Type", "Status", "Viral Score", "Caption", "Sent At"
    ])
    st.dataframe(log_df[["Handle", "Type", "Status", "Viral Score", "Caption", "Sent At"]], use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Export Log CSV",
        data=log_df.to_csv(index=False),
        file_name="content_log.csv",
        mime="text/csv"
    )

# =========================================
# FEATURE: PHOTO COLLAGE MAKER
# =========================================

st.markdown("---")
st.markdown("## 🖼️ Photo Collage Maker")

collage_files = st.file_uploader(
    "Upload 2–6 photos for collage",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="collage_upload"
)

col_l, col_r = st.columns([1, 1])
with col_l:
    collage_layout = st.selectbox("Layout", ["2x2", "3x1", "1x3", "2x3", "3x2"], key="collage_layout")
with col_r:
    collage_title = st.text_input("Title on Collage (optional)", value="@gayatribhardwaj__", key="collage_title")

if st.button("✨ Create Collage") and collage_files:
    import tempfile
    tmp_paths = []
    for f in collage_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
            t.write(f.read())
            tmp_paths.append(t.name)
    try:
        out = make_collage(tmp_paths, layout=collage_layout, title_text=collage_title)
        st.image(Image.open(out), caption="Collage Preview", use_container_width=True)
        with open(out, "rb") as f:
            st.download_button("⬇️ Download Collage", data=f, file_name="collage.jpg")
    except Exception as e:
        st.error(f"Collage error: {e}")
elif st.button("✨ Create Collage"):
    st.warning("Upload at least 2 photos.")

# =========================================
# FEATURE: CINEMATIC STYLE FILTER
# =========================================

st.markdown("---")
st.markdown("## 🎬 Cinematic Style Filter")

filter_file = st.file_uploader("Upload photo to style", type=["jpg", "jpeg", "png"], key="filter_upload")
filter_preset = st.selectbox("Choose Style Preset", list(STYLE_PRESETS.keys()), key="filter_preset")

if st.button("🎨 Apply Style Filter") and filter_file:
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
        t.write(filter_file.read())
        tmp_path = t.name
    try:
        out = apply_style_filter(tmp_path, filter_preset)
        c1, c2 = st.columns(2)
        with c1:
            st.image(Image.open(tmp_path), caption="Original", use_container_width=True)
        with c2:
            st.image(Image.open(out), caption=f"{filter_preset} Filter", use_container_width=True)
        with open(out, "rb") as f:
            st.download_button("⬇️ Download Styled Photo", data=f, file_name=f"{filter_preset.lower().replace(' ','_')}.jpg")
    except Exception as e:
        st.error(f"Filter error: {e}")

# =========================================
# FEATURE: AI STYLE EDIT (Stability AI)
# =========================================

st.markdown("---")
st.markdown("## 🤖 AI Style Edit (img2img)")
st.caption("Uses Stability AI free tier — get free key at platform.stability.ai | Or uses local filter as fallback")

ai_edit_file = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png"], key="ai_edit_upload")

ai_presets = {
    "Cinematic Edit": "cinematic film still, dramatic lighting, 8k, highly detailed, aesthetic",
    "Saree Look": "wearing elegant silk saree, traditional Indian outfit, golden border, soft studio lighting",
    "Western Dress": "wearing stylish western dress, fashion editorial, clean background, high fashion",
    "Royal Look": "wearing royal Indian lehenga, jewellery, regal pose, soft bokeh background",
    "Street Style": "wearing trendy street fashion, urban background, candid natural light",
    "Custom Prompt": ""
}

ai_style_choice = st.selectbox("Style Preset", list(ai_presets.keys()), key="ai_style_choice")
ai_prompt_text = ai_presets[ai_style_choice]
if ai_style_choice == "Custom Prompt":
    ai_prompt_text = st.text_area("Write your prompt", placeholder="cinematic lighting, golden hour, beautiful...")

ai_strength = st.slider("Edit Strength (higher = more AI, lower = closer to original)", 0.3, 0.9, 0.6, 0.05)

if st.button("🚀 Generate AI Edit") and ai_edit_file:
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
        t.write(ai_edit_file.read())
        tmp_path = t.name
    with st.spinner("Generating AI edit..."):
        try:
            out_path, msg = ai_style_edit(tmp_path, ai_prompt_text, strength=ai_strength)
            st.info(msg)
            c1, c2 = st.columns(2)
            with c1:
                st.image(Image.open(tmp_path), caption="Original", use_container_width=True)
            with c2:
                st.image(Image.open(out_path), caption="AI Edited", use_container_width=True)
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Download AI Edit", data=f, file_name="ai_edit.jpg")
        except Exception as e:
            st.error(f"AI edit failed: {e}")
