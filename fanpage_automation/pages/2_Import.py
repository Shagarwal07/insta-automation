import json
import math
import streamlit as st
from core_engine import (
    extract_shortcode, detect_post_type, generate_caption,
    download_photo_post, send_carousel_to_telegram, send_message_to_telegram
)
from theme import THEME_CSS

st.set_page_config(page_title="Import · Gayu_theHelper", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.markdown("<a href='/' style='color:#e8006e;font-weight:600;text-decoration:none;'>← Back to Dashboard</a>", unsafe_allow_html=True)
st.markdown("## 📦 Import Scraped JSON")

col1, col2 = st.columns(2)
with col1:
    style = st.selectbox("Caption Style", ["Dreamy", "Main Character", "Trending"])
with col2:
    content_mode = st.selectbox("Content Mode", ["Photo Posts", "Solo Pics Only", "High Engagement Photos", "Reels Only"])

uploaded_json = st.file_uploader("Upload Instagram scraped JSON", type=["json"])

def clean_json_posts(data):
    if not isinstance(data, list):
        data = [data]
    unique_posts, seen = [], set()
    for item in data:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or item.get("post_url") or item.get("link")
               or item.get("instagramUrl") or item.get("shortCodeUrl"))
        if not url:
            continue
        url = url.split("?")[0].strip()
        key = extract_shortcode(url) or url
        if key in seen:
            continue
        seen.add(key)
        item["_clean_url"] = url
        unique_posts.append(item)
    return unique_posts

if uploaded_json:
    try:
        data = json.load(uploaded_json)
        total_items = len(data) if isinstance(data, list) else 1
        st.success(f"✨ Loaded {total_items} items")

        c1, c2, c3 = st.columns(3)
        c1.metric("Posts Found", total_items)
        c2.metric("Type", "Instagram")
        c3.metric("Ready", "Yes ✅")

        with st.expander("Preview first item"):
            st.write(data[0] if isinstance(data, list) else data)

        cleaned_posts = clean_json_posts(data)
        batch_size = 10
        total_posts = len(cleaned_posts)
        num_batches = math.ceil(total_posts / batch_size)

        st.markdown(f"### 🚀 Batch Processing — {total_posts} posts, {num_batches} batches")

        for i in range(0, num_batches, 5):
            btn_cols = st.columns(5)
            for j in range(5):
                batch_idx = i + j
                if batch_idx >= num_batches:
                    break
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, total_posts)
                if btn_cols[j].button(f"Batch {batch_idx + 1}", key=f"batch_{batch_idx}"):
                    processed = failed = 0
                    progress = st.progress(0)
                    for idx, item in enumerate(cleaned_posts[start_idx:end_idx]):
                        try:
                            url = item["_clean_url"]
                            post_type = detect_post_type(url)
                            caption = generate_caption(style, content_mode)
                            if post_type == "photo":
                                paths = download_photo_post(url)
                                send_carousel_to_telegram(paths, caption, url)
                            elif post_type == "reel":
                                send_message_to_telegram(f"🎬 Reel\n\n{url}\n\n{caption}")
                            processed += 1
                        except Exception as e:
                            failed += 1
                            st.error(f"Error: {e}")
                        progress.progress((idx + 1) / (end_idx - start_idx))
                    st.success(f"Batch {batch_idx + 1} done — ✅ {processed} sent, ❌ {failed} failed")
    except Exception as e:
        st.error(f"Invalid JSON: {e}")
