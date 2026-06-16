import pandas as pd
import streamlit as st
from core_engine import get_content_log, get_best_posting_times
from theme import THEME_CSS

st.set_page_config(page_title="Analytics · Gayu_theHelper", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.markdown("<a href='/' style='color:#e8006e;font-weight:600;text-decoration:none;'>← Back to Dashboard</a>", unsafe_allow_html=True)
st.markdown("## 📊 Analytics & Planning")

# ── POSTING TIMES ──
st.markdown("### 🕐 Best Posting Times")
times = get_best_posting_times()
time_df = pd.DataFrame(times)
st.dataframe(time_df, use_container_width=True, hide_index=True)
st.download_button("📅 Download Schedule", data=time_df.to_csv(index=False), file_name="schedule.csv", mime="text/csv")

st.markdown("---")

# ── CONTENT LOG ──
st.markdown("### 📅 Content Sent Log")
log_rows = get_content_log()
if not log_rows:
    st.info("No sent posts yet. Send some content first.")
else:
    log_df = pd.DataFrame(log_rows, columns=["Handle","Shortcode","URL","Type","Status","Viral Score","Caption","Sent At"])
    display_df = log_df[["Handle","Type","Status","Viral Score","Caption","Sent At"]]

    total = len(log_df)
    photos = len(log_df[log_df["Type"] == "photo"])
    reels = len(log_df[log_df["Type"] == "reel"])
    avg_score = round(log_df["Viral Score"].mean(), 1) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sent", total)
    c2.metric("Photos", photos)
    c3.metric("Reels", reels)
    c4.metric("Avg Viral Score", avg_score)

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Export CSV", data=log_df.to_csv(index=False), file_name="content_log.csv", mime="text/csv")
