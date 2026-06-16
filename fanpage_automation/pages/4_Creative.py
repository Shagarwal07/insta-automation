import tempfile
import streamlit as st
from PIL import Image
from core_engine import (
    add_watermark, make_collage, apply_style_filter,
    ai_style_edit, costume_transfer, STYLE_PRESETS
)
from theme import THEME_CSS

st.set_page_config(page_title="Creative · Gayu_theHelper", page_icon="🎨", layout="wide", initial_sidebar_state="collapsed")
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.markdown("<a href='/' style='color:#e8006e;font-weight:600;text-decoration:none;'>← Back to Dashboard</a>", unsafe_allow_html=True)
st.markdown("## 🎨 Creative Tools")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🖊️ Watermark", "🖼️ Collage", "🎬 Style Filter", "🤖 AI Edit", "👗 Costume Transfer"])

# ── WATERMARK ──
with tab1:
    st.markdown("### 🖊️ Watermark Tool")
    wm_text = st.text_input("Watermark Text", value="@gayatribhardwaj__")
    wm_file = st.file_uploader("Upload Image", type=["jpg","jpeg","png"], key="wm_upload")
    if st.button("💧 Apply Watermark", key="wm_btn") and wm_file:
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

# ── COLLAGE ──
with tab2:
    st.markdown("### 🖼️ Photo Collage Maker")
    collage_files = st.file_uploader("Upload 2–6 photos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="collage_up")
    c1, c2 = st.columns(2)
    layout = c1.selectbox("Layout", ["2x2","3x1","1x3","2x3","3x2"])
    title = c2.text_input("Title (optional)", value="@gayatribhardwaj__")
    if st.button("✨ Create Collage", key="collage_btn"):
        if collage_files:
            tmp_paths = []
            for f in collage_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
                    t.write(f.read()); tmp_paths.append(t.name)
            try:
                out = make_collage(tmp_paths, layout=layout, title_text=title)
                st.image(Image.open(out), caption="Collage", use_container_width=True)
                with open(out, "rb") as f:
                    st.download_button("⬇️ Download Collage", data=f, file_name="collage.jpg", key="dl_collage")
            except Exception as e:
                st.error(str(e))
        else:
            st.warning("Upload at least 2 photos.")

# ── STYLE FILTER ──
with tab3:
    st.markdown("### 🎬 Cinematic Style Filter")
    filter_file = st.file_uploader("Upload photo", type=["jpg","jpeg","png"], key="filter_up")
    preset = st.selectbox("Preset", list(STYLE_PRESETS.keys()))
    if st.button("🎨 Apply Filter", key="filter_btn") and filter_file:
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

# ── AI EDIT ──
with tab4:
    st.markdown("### 🤖 AI Style Edit (Stability AI)")
    st.caption("Free tier: 25 credits/month at platform.stability.ai")
    ai_file = st.file_uploader("Upload photo", type=["jpg","jpeg","png"], key="ai_up")
    ai_presets = {
        "Cinematic Edit": "cinematic film still, dramatic lighting, 8k, highly detailed",
        "Saree Look": "wearing elegant silk saree, traditional Indian outfit, golden border",
        "Western Dress": "wearing stylish western dress, fashion editorial, clean background",
        "Royal Look": "wearing royal Indian lehenga, jewellery, regal pose, bokeh background",
        "Street Style": "wearing trendy street fashion, urban background, candid natural light",
        "Custom": ""
    }
    choice = st.selectbox("Style Preset", list(ai_presets.keys()), key="ai_preset")
    prompt = ai_presets[choice]
    if choice == "Custom":
        prompt = st.text_area("Custom prompt", placeholder="cinematic lighting, golden hour...")
    strength = st.slider("Edit Strength", 0.3, 0.9, 0.6, 0.05, key="ai_strength")
    if st.button("🚀 Generate AI Edit", key="ai_btn") and ai_file:
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

# ── COSTUME TRANSFER ──
with tab5:
    st.markdown("### 👗 Costume Transfer")
    st.caption("Gemini reads the reference costume → Stability AI applies it to the person photo")
    c1, c2 = st.columns(2)
    with c1:
        person_file = st.file_uploader("Person Photo", type=["jpg","jpeg","png"], key="ct_person")
        if person_file: st.image(person_file, caption="Person", use_container_width=True)
    with c2:
        costume_file = st.file_uploader("Reference Costume", type=["jpg","jpeg","png"], key="ct_costume")
        if costume_file: st.image(costume_file, caption="Costume", use_container_width=True)
    ct_strength = st.slider("Transfer Strength", 0.4, 0.9, 0.7, 0.05, key="ct_str")
    if st.button("👗 Apply Costume Transfer", key="ct_btn"):
        if person_file and costume_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tp:
                tp.write(person_file.read()); p_tmp = tp.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tc:
                tc.write(costume_file.read()); c_tmp = tc.name
            with st.spinner("Reading costume with Gemini → applying with Stability AI..."):
                try:
                    out, msg = costume_transfer(p_tmp, c_tmp, strength=ct_strength)
                    st.success(msg)
                    st.image(Image.open(out), caption="Result", use_container_width=True)
                    with open(out, "rb") as f:
                        st.download_button("⬇️ Download", data=f, file_name="costume_result.jpg", key="dl_ct")
                except Exception as e:
                    st.error(str(e))
        else:
            st.warning("Upload both photos.")
