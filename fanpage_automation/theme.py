THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

html, body, .stApp, [class*="css"] { font-family: 'Poppins', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #fff0f6 0%, #fce4f0 50%, #f5d0e8 100%) !important;
    color: #2d1320 !important;
}

header, [data-testid="stHeader"] { background: transparent !important; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#ffe0ee,#ffc8df) !important;
    border-right: 2px solid #f0a0c0;
    box-shadow: 4px 0 20px rgba(255,80,150,0.1);
}
section[data-testid="stSidebar"] * { color: #2d1320 !important; }

h1,h2,h3,h4,p,label,span { color: #2d1320 !important; }

/* File uploader fix */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.88) !important;
    border: 2px dashed #f0a0c0 !important;
    border-radius: 16px !important;
}
[data-testid="stFileUploader"] * { color: #2d1320 !important; background: transparent !important; }
[data-testid="stFileUploaderDropzone"] { background: rgba(255,240,248,0.95) !important; border-radius: 14px !important; }
section[data-testid="stFileUploaderDropzoneInput"] + div { color: #2d1320 !important; }

/* Inputs */
input, textarea {
    background: rgba(255,255,255,0.92) !important;
    color: #2d1320 !important;
    border: 1.5px solid #f0a0c0 !important;
    border-radius: 12px !important;
}

/* Selectbox */
div[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.92) !important;
    border: 1.5px solid #f0a0c0 !important;
    border-radius: 12px !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div { color: #2d1320 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #ff6fab, #e8006e) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.5rem !important;
    box-shadow: 0 4px 15px rgba(232,0,110,0.3) !important;
    transition: box-shadow 0.2s, transform 0.2s !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 22px rgba(232,0,110,0.45) !important;
    transform: translateY(-2px) !important;
    background: linear-gradient(135deg, #ff4d94, #c8005e) !important;
}

/* Cards */
.card {
    background: rgba(255,255,255,0.82);
    border: 1px solid #ffc2d6;
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 18px;
    box-shadow: 0 6px 24px rgba(255,80,150,0.1);
    backdrop-filter: blur(6px);
}

/* Metric containers */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.85) !important;
    border: 1px solid #ffc2d6 !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 14px rgba(255,80,150,0.08) !important;
}

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 14px !important; overflow: hidden !important; }

/* Progress bar */
.stProgress > div > div { background: linear-gradient(90deg,#ff6fab,#e8006e) !important; }

/* Slider */
[data-testid="stSlider"] div[data-testid="stSliderThumb"] { background: #e8006e !important; }

/* Nav menu custom */
.nav-menu {
    display: flex;
    gap: 8px;
    padding: 10px 0 18px 0;
    flex-wrap: wrap;
}
.nav-btn {
    background: rgba(255,255,255,0.7);
    border: 1.5px solid #f0a0c0;
    border-radius: 22px;
    padding: 8px 20px;
    color: #c0006e !important;
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.18s;
    text-decoration: none;
}
.nav-btn:hover, .nav-btn.active {
    background: linear-gradient(135deg,#ff6fab,#e8006e);
    color: white !important;
    border-color: transparent;
    box-shadow: 0 4px 14px rgba(232,0,110,0.3);
}
</style>
"""

HERO_HTML = """
<div style="background:linear-gradient(135deg,rgba(255,255,255,0.88),rgba(255,210,230,0.75));
     border:1px solid #ffc2d6;border-radius:28px;padding:40px 36px;text-align:center;
     box-shadow:0 10px 40px rgba(255,60,140,0.15);margin-bottom:28px;backdrop-filter:blur(12px);">
    <div style="font-size:52px;margin-bottom:6px;">🌸</div>
    <div style="background:linear-gradient(90deg,#ff4d94,#c8005e);-webkit-background-clip:text;
         -webkit-text-fill-color:transparent;font-size:46px;font-weight:800;letter-spacing:-1px;">
         Gayu_theHelper</div>
    <div style="color:#9d4b6c;font-size:16px;margin-top:4px;">Your Dreamy Content Companion ✨</div>
    <div style="margin-top:14px;display:flex;justify-content:center;gap:10px;flex-wrap:wrap;">
        <span style="background:#ff6fab22;color:#c0006e;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;">🤖 AI Powered</span>
        <span style="background:#ff6fab22;color:#c0006e;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;">📸 Photo Tools</span>
        <span style="background:#ff6fab22;color:#c0006e;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;">💬 Caption Gen</span>
        <span style="background:#ff6fab22;color:#c0006e;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;">👗 Style Edit</span>
    </div>
</div>
"""
