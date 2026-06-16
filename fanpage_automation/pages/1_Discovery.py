import streamlit as st
from core_engine import (
    clean_handles, sync_data, clear_old_data,
    deep_search_and_send, smart_discovery_ai, deep_discovery_ai
)
from theme import THEME_CSS

st.set_page_config(page_title="Discovery · Gayu_theHelper", page_icon="🔍", layout="wide", initial_sidebar_state="collapsed")
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.markdown("<a href='/' style='color:#e8006e;font-weight:600;text-decoration:none;'>← Back to Dashboard</a>", unsafe_allow_html=True)
st.markdown("## 🔍 Content Discovery")

handles_input = st.text_input("Instagram Handles (one per line)", value="@gayatribhardwaj__")
handles = clean_handles(handles_input)

col1, col2 = st.columns(2)
with col1:
    content_mode = st.selectbox("Content Mode", ["Photo Posts", "Solo Pics Only", "High Engagement Photos", "Reels Only"])
with col2:
    deep_mode = st.selectbox("Deep Search Mode", ["Hidden Gems", "Photoshoots", "Candid Looks", "Event Looks", "High Reach Looks"])

c1, c2, c3 = st.columns(3)

with c1:
    if st.button("🔄 Sync Data"):
        with st.spinner("Syncing..."):
            try:
                count = sync_data(handles, content_mode)
                st.success(f"Synced {count} posts!")
            except Exception as e:
                st.error(str(e))
    if st.button("🗑 Clear All Data"):
        clear_old_data()
        st.success("Cleared.")

with c2:
    deep_limit = st.slider("Photos to find", 5, 30, 10, 5)
    if st.button("🔎 Deep Search & Send"):
        with st.spinner("Searching..."):
            try:
                result = deep_search_and_send(handles=handles, deep_mode=deep_mode, limit=deep_limit)
                st.success(result)
            except Exception as e:
                st.error(str(e))

with c3:
    smart_limit = st.select_slider("AI Limit", options=[3, 5, 10], value=5)
    if st.button("🚀 Smart Discovery AI"):
        with st.spinner("Running AI discovery..."):
            try:
                mode_slug = deep_mode.lower().replace(" ", "_")
                result = smart_discovery_ai(handles=handles, deep_mode=mode_slug, limit=smart_limit)
                st.success(result)
            except Exception as e:
                st.error(str(e))

st.markdown("---")
st.markdown("### 🌌 Deep Discovery AI")
discovery_handles = st.text_area("Discovery Handles", value="@gayatribhardwaj__")
prompt_file = st.file_uploader("Custom prompt (optional .txt)", type=["txt"])
custom_p = None
if prompt_file:
    try:
        custom_p = prompt_file.read().decode("utf-8")
    except Exception:
        pass

if st.button("🚀 Start Deep Discovery AI"):
    with st.spinner("Running Deep Discovery..."):
        try:
            mode_slug = deep_mode.lower().replace(" ", "_")
            result = deep_discovery_ai(
                handles=clean_handles(discovery_handles),
                deep_mode=mode_slug, limit=10,
                custom_prompt=custom_p
            )
            st.success(result)
        except Exception as e:
            st.error(str(e))
