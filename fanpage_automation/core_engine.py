import hashlib
import os
import cv2
import re
import glob
import random
import time
from urllib.parse import urlparse
import json
import sqlite3
import requests
from serpapi import GoogleSearch
from dotenv import load_dotenv
import instaloader
import google.generativeai as genai
from groq import Groq
from PIL import Image
from io import BytesIO
import uuid

load_dotenv()

DB_PATH = "fanpage_data.db"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Instaloader once for reuse
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")
L = instaloader.Instaloader(
    dirname_pattern="downloads/photos/{target}",
    save_metadata=False,
    download_comments=False,
    download_video_thumbnails=False,
    compress_json=False
)

# -------------------------
# AI FALLBACK ORCHESTRATOR
# -------------------------

def ai_layer_orchestrator(post_data):
    """
    AI fallback order:
    OpenRouter -> Groq -> Local Template

    Gemini removed from this function to avoid quota exhaustion.
    """

    prompt = f"""
{FANPAGE_SYSTEM_PROMPT}

Analyze this metadata and return valid JSON only:

{json.dumps(post_data, indent=2)}

Return format:
{{
  "decision": "POST",
  "viral_score": 75,
  "engagement_rating": "High",
  "caption": "short aesthetic caption",
  "reason": "short reason"
}}
"""

    # 1. OpenRouter first
    or_key = os.getenv("OPENROUTER_API_KEY")

    print("OPENROUTER KEY FOUND:", bool(or_key))

    if or_key:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8501",
                    "X-Title": "Gayu_theHelper"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Return valid JSON only. No markdown."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7
                },
                timeout=60
            )

            print("OpenRouter Status:", response.status_code)
            print("OpenRouter Response:", response.text[:500])

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return clean_gemini_json(content)
        except Exception as e:
            print(f"OpenRouter Layer Failed: {e}")

    # 2. Groq second
    groq_key = os.getenv("GROQ_API_KEY")

    if groq_key:
        try:
            client = Groq(api_key=groq_key)

            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "Return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )

            return json.loads(
                chat_completion.choices[0].message.content
            )

        except Exception as e:
            print(f"Groq Layer Failed: {e}")

    # 3. Local fallback only
    return {
        "decision": "POST",
        "viral_score": 60,
        "engagement_rating": "Unknown",
        "caption": generate_caption("Dreamy", "Normal"),
        "reason": "AI unavailable, used local template."
    }

# -------------------------
# OPENCV LOCAL FILTERS
# -------------------------

def local_quality_filter(image_path):
    if not os.path.exists(image_path):
        return True, "Skipped CV: file missing"

    img = cv2.imread(image_path)

    if img is None:
        return False, "Unreadable image"

    h, w = img.shape[:2]

    # reject very tiny images only
    if w < 250 or h < 250:
        return False, "Image too small"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # blur check, softer
    blur = cv2.Laplacian(gray, cv2.CV_64F).var()

    if blur < 25:
        return False, f"Too blurry: {blur:.2f}"

    # face detection should add score, not reject
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    return True, f"Passed. Faces detected: {len(faces)}, blur: {blur:.2f}"

def filter_discovery_results(results):
    """
    Filters search results to ensure they match the target persona 
    and aren't low-quality or incorrect media types.
    """
    approved = []
    blocked = [
        "/reel/", "/reels/", "/profile", "?hl=", 
        "facebook.com", "youtube.com", "lookaside", 
        "ytimg", "video", "watch"
    ]
    required_words = ["gayatri", "bhardwaj"]

    for item in results:
        source = (item.get("link") or item.get("source_url") or "").lower()
        image = (item.get("original") or item.get("image_url") or item.get("thumbnail") or "").lower()
        title = item.get("title", "").lower()

        if any(x in source for x in blocked): continue
        if any(x in image for x in blocked): continue
        
        if any(x in title or x in source for x in required_words):
            approved.append(item)
            
    return approved

def download_generic_image(image_url, source_url=None):
    """
    Downloads and validates an image file from a direct URL.
    Converts to standard RGB JPEG to ensure Telegram compatibility.
    """
    os.makedirs("downloads/deep_images", exist_ok=True)
    
    blocked_domains = ["lookaside.fbsbx.com", "lookaside.instagram.com", "ytimg.com", "youtube.com"]
    if any(domain in image_url for domain in blocked_domains):
        raise Exception(f"Blocked unstable crawler URL: {image_url}")

    filepath = f"downloads/deep_images/{uuid.uuid4()}.jpg"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(image_url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Download failed with status: {response.status_code}")

    try:
        img = Image.open(BytesIO(response.content))
        img = img.convert("RGB")
        img.save(filepath, "JPEG", quality=95)
    except Exception as e:
        raise Exception(f"Invalid image file: {e}")

    return filepath

def smart_discovery_ai(handles, deep_mode, limit=5, discovery_engine="google_images"):
    """
    Advanced discovery combining Search, local Computer Vision, and tiered AI Analysis.
    """
    serp_api_key = os.getenv("SERP_API_KEY")
    discovery_results = []
    seen = set()

    for handle in handles:
        queries = build_discovery_queries(handle, deep_mode)
        for query in queries:
            search = GoogleSearch({
                "q": query,
                "api_key": serp_api_key,
                "engine": discovery_engine,
                "ijn": random.randint(0, 8),
                "num": 20
            })
            items = search.get_dict().get("images_results", [])
            
            # Initial filter based on keywords
            filtered_items = filter_discovery_results(items)
            print(f"DEBUG: Found {len(items)} raw items, {len(filtered_items)} passed keyword filter.")
            
            for item in filtered_items:
                img_url = item.get("original")
                if not img_url or img_url in seen: continue
                seen.add(img_url)
                
                try:
                    # Download first for local checking
                    local_file = download_generic_image(img_url)
                    
                    # Local OpenCV Filters
                    passed, reason = local_quality_filter(local_file)
                    if not passed:
                        print(f"DEBUG: Image {img_url} rejected: {reason}")
                        os.remove(local_file)
                        continue
                    
                    discovery_results.append({
                        "local_file": local_file,
                        "source_url": item.get("source_url", ""),
                        "metadata": item
                    })
                    
                    if len(discovery_results) >= limit: break
                except Exception as e: 
                    print(f"DEBUG: Exception during local processing of {img_url}: {e}")
                    continue
            if len(discovery_results) >= limit: break

    # Finalize Top items with AI Layer
    sent = 0
    print(f"DEBUG: Proceeding to AI Analysis with {len(discovery_results)} local candidates.")
    
    for entry in discovery_results:
        ai_res = ai_layer_orchestrator(entry['metadata'])
        if ai_res.get("decision") == "SKIP" and ai_res.get("viral_score", 50) < 40:
            print(f"DEBUG: AI rejected candidate from {entry['source_url']}. Reason: {ai_res.get('reason')}")
            if os.path.exists(entry['local_file']): os.remove(entry['local_file'])
            continue
            
        caption = f"🧠 **Smart Discovery AI**\n\n🔥 Score: {ai_res.get('viral_score')}/100\n\n{ai_res.get('caption')}"
        send_photo_to_telegram(entry['local_file'], caption, entry['source_url'])
        sent += 1
        
    return f"Smart Discovery finished. Sent {sent} high-quality photos."


# -------------------------
# DATABASE
# -------------------------

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT,
            shortcode TEXT UNIQUE,
            url TEXT,
            post_type TEXT,
            content_mode TEXT,
            status TEXT DEFAULT 'PENDING',
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def local_deep_score(item):
    title = item.get("title", "").lower()
    source = item.get("source_url", "").lower()
    image = item.get("image_url", "").lower()

    score = 0

    positive = [
        "gayatri",
        "bhardwaj",
        "photoshoot",
        "candid",
        "solo",
        "portrait",
        "fashion",
        "event",
        "actress",
        "glamorous",
        "style"
    ]

    negative = [
        "youtube",
        "reel",
        "reels",
        "profile",
        "facebook",
        "lookaside",
        "ytimg",
        "video",
        "watch",
        "group",
        "meme",
        "poster"
    ]

    for word in positive:
        if word in title or word in source:
            score += 10

    for word in negative:
        if word in title or word in source or word in image:
            score -= 40

    if image.endswith((".jpg", ".jpeg", ".png", ".webp")):
        score += 20

    if "pinterest" in source:
        score += 10

    if "instagram.com/p/" in source:
        score += 10

    return {
        "decision": "POST" if score >= 45 else "SKIP",
        "score": max(0, min(score, 100)),
        "category": "Rule-Based Deep Pick",
        "reason": "Selected using local scoring without Gemini."
    }

def clear_old_data():
    conn = get_conn()
    conn.execute("DELETE FROM posts")
    conn.commit()
    conn.close()


def migrate_db():
    conn = get_conn()
    columns = [
        "viral_score INTEGER DEFAULT 0",
        "engagement_rating TEXT",
        "content_category TEXT",
        "reason TEXT",
        "gemini_caption TEXT",
        "gemini_json TEXT"
    ]
    for col in columns:
        try:
            conn.execute(f"ALTER TABLE posts ADD COLUMN {col}")
        except:
            pass
    conn.commit()
    conn.close()


def update_status(post_id, status, caption=None):
    conn = get_conn()
    conn.execute("""
        UPDATE posts
        SET status = ?, caption = ?
        WHERE id = ?
    """, (status, caption, post_id))
    conn.commit()
    conn.close()


# -------------------------
# HELPERS
# -------------------------

def clean_handles(raw_text):
    return [
        h.strip().replace("@", "")
        for h in raw_text.splitlines()
        if h.strip()
    ]


def detect_post_type(url):
    if "/reel/" in url:
        return "reel"
    if "/p/" in url:
        return "photo"
    return "unknown"


def extract_shortcode(url):
    path = urlparse(url).path
    return path.strip("/").split("/")[-1]


def build_query(handle, content_mode):
    name = handle.replace("@", "").strip()

    queries = {
        "Photo Posts": f'site:instagram.com/p "{name}"',
        "Solo Pics Only": f'site:instagram.com/p "{name}" "solo" OR "portrait" OR "photoshoot"',
        "High Engagement Photos": f'site:instagram.com/p "{name}" "likes" OR "comments" OR "viral"',
        "Reels Only": f'site:instagram.com/reel "{name}"'
    }

    return queries.get(content_mode, f'site:instagram.com/p "{name}"')


# -------------------------
# CAPTION ENGINE - NO OPENAI
# -------------------------

def clean_gemini_json(text):
    text = text.strip()
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == -1:
        raise Exception("Gemini did not return JSON")
    return json.loads(text[start:end])


FANPAGE_SYSTEM_PROMPT = """
You are a Fanpage Content Strategist AI.

Tasks:
- Analyze Instagram post metadata
- Score content quality
- Detect solo-photo potential
- Detect viral potential
- Reject weak posts
- Generate trendy captions
- Return JSON only
"""

CAPTIONS = {
    "Dreamy": [
        "some frames feel like poetry ✨",
        "soft smile, golden energy 🤍",
        "a moment worth saving 🌙",
        "she makes simple moments cinematic ✨"
    ],
    "Main Character": [
        "main character energy, effortlessly.",
        "this look had its own storyline.",
        "the screen belongs to her.",
        "not acting, just aura."
    ],
    "Trending": [
        "this frame deserves more attention 👀",
        "underrated for no reason.",
        "replay-worthy energy.",
        "wait, this look >>>"
    ]
}

HASHTAGS = "#GayatriBhardwaj #Fanpage #IndianActress #AestheticEdit #ReelsIndia"


def generate_caption(style, content_mode):
    caption = random.choice(CAPTIONS.get(style, CAPTIONS["Dreamy"]))

    if content_mode == "Solo Pics Only":
        hook = "solo frame, full aura ✨"
    elif content_mode == "High Engagement Photos":
        hook = "this one deserves all the attention 👀"
    elif content_mode == "Reels Only":
        hook = "reel idea worth saving 🎬"
    else:
        hook = caption

    return f"{hook}\n\n{caption}\n\n{HASHTAGS}"


def analyze_post_with_gemini(post_data):
    prompt = f"""
You are Gayu_theHelper, a dreamy Instagram content strategist.

Analyze this Instagram post metadata and return ONLY valid JSON.

Task:
1. Judge if this post is worth posting.
2. Give viral score from 0 to 100.
3. Give engagement rating.
4. Generate UNIQUE caption.
5. Generate hooks and hashtags.

Important:
- Caption must be unique every time.
- Do not repeat same captions like "some frames feel like poetry".
- Avoid cringe.
- Keep it short, trendy, aesthetic.
- If likes/comments are missing, estimate based on available metadata.
- If post looks weak, decision should be SKIP.
- If it is likely solo/photo/aesthetic, decision should be POST.

Scoring:
Solo / actress focused: 25
Aesthetic value: 20
Engagement signal: 20
Fanpage value: 20
Freshness: 15

Return JSON only in this format:

{{
  "decision": "POST or SKIP",
  "viral_score": 0,
  "engagement_rating": "Low / Medium / High / Very High",
  "content_category": "Solo Photo / Reel / Carousel / Weak Content",
  "reason": "short reason",
  "caption": "unique caption",
  "hooks": ["hook1", "hook2", "hook3"],
  "hashtags": ["#GayatriBhardwaj", "#Fanpage"],
  "telegram_message": "ready message"
}}

Post data:
{json.dumps(post_data, indent=2)}
"""
    response = gemini_model.generate_content(prompt)
    return clean_gemini_json(response.text)


def save_post_with_gemini(handle, shortcode, url, post_type, content_mode, metadata=None):
    metadata = metadata or {}
    post_data = {
        "handle": handle,
        "shortcode": shortcode,
        "url": url,
        "post_type": post_type,
        "content_mode": content_mode,
        "likes": metadata.get("likes") or metadata.get("likesCount"),
        "comments": metadata.get("comments") or metadata.get("commentsCount"),
        "caption_text": metadata.get("caption") or metadata.get("caption_text"),
        "video_play_count": metadata.get("videoPlayCount"),
        "timestamp": metadata.get("timestamp") or metadata.get("takenAt"),
        "unique_seed": f"{shortcode}-{random.randint(1000,9999)}"
    }

    try:
        gem = analyze_post_with_gemini(post_data)
    except Exception as e:
        gem = {
            "decision": "POST",
            "viral_score": 55,
            "engagement_rating": "Unknown",
            "content_category": post_type,
            "reason": f"Gemini failed: {e}",
            "caption": generate_caption("Dreamy", content_mode),
            "hooks": [],
            "hashtags": ["#GayatriBhardwaj", "#Fanpage"],
            "telegram_message": ""
        }

    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO posts
        (
            handle, shortcode, url, post_type, content_mode, status,
            viral_score, engagement_rating, content_category,
            reason, gemini_caption, gemini_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        handle, shortcode, url, post_type, content_mode,
        "PENDING" if gem["decision"] == "POST" else "SKIPPED",
        gem.get("viral_score", 0),
        gem.get("engagement_rating", "Unknown"),
        gem.get("content_category", post_type),
        gem.get("reason", ""),
        gem.get("caption", ""),
        json.dumps(gem)
    ))
    conn.commit()
    conn.close()


def get_posts(handles):
    if not handles:
        return []
    placeholders = ",".join(["?"] * len(handles))
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT id, handle, shortcode, url, post_type, content_mode, status,
               viral_score, engagement_rating, content_category, reason, gemini_caption
        FROM posts
        WHERE handle IN ({placeholders})
        ORDER BY viral_score DESC, created_at DESC
    """, handles).fetchall()
    conn.close()
    return rows


def get_gemini_caption_from_db(post_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT gemini_caption FROM posts WHERE id = ?",
        (post_id,) # Ensure post_id is a tuple for parameter binding
    ).fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return generate_caption("Dreamy", "Photo Posts")


def get_file_hash(file_path):
    """Generates a SHA256 hash of a file to detect duplicates."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def remove_duplicate_images(image_paths):
    unique_images = []
    seen_hashes = set()
    for image_path in image_paths:
        try:
            file_hash = get_file_hash(image_path)
            if file_hash not in seen_hashes:
                seen_hashes.add(file_hash)
                unique_images.append(image_path)
        except Exception:
            continue
    return unique_images


def download_photo_post(url):
    os.makedirs("downloads/photos", exist_ok=True)
    shortcode = extract_shortcode(url)

    # Track existing files to identify new downloads
    before_files = set(glob.glob(f"downloads/photos/{shortcode}/*"))

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=shortcode)
    except Exception as e:
        print(f"Instaloader warning: {e}")

    after_files = set(glob.glob(f"downloads/photos/{shortcode}/*"))
    new_files = list(after_files - before_files)

    image_paths = [
        f for f in new_files
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    # Fallback: if no new files were identified, look at existing ones in folder
    if not image_paths:
        image_paths = glob.glob(f"downloads/photos/{shortcode}/*.jpg")
        image_paths += glob.glob(f"downloads/photos/{shortcode}/*.jpeg")
        image_paths += glob.glob(f"downloads/photos/{shortcode}/*.png")

    image_paths = sorted(image_paths)
    image_paths = remove_duplicate_images(image_paths)

    if not image_paths:
        raise Exception("No photo found. This may be reel/video-only post.")

    return image_paths


# -------------------------
# TELEGRAM DELIVERY
# -------------------------

def send_message_to_telegram(message):
    """Sends a text message to the Telegram channel."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        },
        timeout=30
    )
    return response.json()


def send_photo_to_telegram(image_path, caption, source_url):
    """Sends a single photo with caption to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    final_caption = f"{caption}\n\nSource: {source_url}"
    with open(image_path, "rb") as photo:
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "caption": final_caption,
                "parse_mode": "HTML"
            },
            files={"photo": photo},
            timeout=60
        )
    return response.json()


def send_carousel_to_telegram(image_paths, caption, source_url):
    """Sends multiple unique photos sequentially to Telegram."""
    unique_images = remove_duplicate_images(image_paths)
    total = len(unique_images)
    for index, image_path in enumerate(unique_images, start=1):
        photo_caption = caption
        if total > 1:
            photo_caption = f"{caption}\n\nCarousel photo {index}/{total}"
        send_photo_to_telegram(
            image_path=image_path,
            caption=photo_caption,
            source_url=source_url
        )
        time.sleep(1)
    return total


# -------------------------
# FETCH + SYNC DATA
# -------------------------

def sync_data(handles, content_mode):
    if not handles:
        return 0

    serp_api_key = os.getenv("SERP_API_KEY")
    if not serp_api_key:
        raise Exception("SERP_API_KEY missing in .env")

    total_saved = 0
    for handle in handles:
        query = build_query(handle, content_mode)
        try:
            search = GoogleSearch({
                "q": query,
                "api_key": serp_api_key,
                "num": 15
            })
            results = search.get_dict()
            organic = results.get("organic_results", [])

            for item in organic:
                url = item.get("link", "")
                if not url or "instagram.com" not in url:
                    continue
                if "/p/" not in url and "/reel/" not in url:
                    continue

                try:
                    shortcode = extract_shortcode(url)
                    post_type = detect_post_type(url)

                    # Metadata simulation for Gemini analysis
                    metadata = {
                        "caption": item.get("snippet", ""),
                        "likesCount": random.randint(1000, 50000),
                        "commentsCount": random.randint(50, 5000)
                    }

                    save_post_with_gemini(
                        handle=handle,
                        shortcode=shortcode,
                        url=url,
                        post_type=post_type,
                        content_mode=content_mode,
                        metadata=metadata
                    )
                    total_saved += 1
                except Exception as inner:
                    print(f"Post skipped: {inner}")
        except Exception as e:
            print(f"Handle error {handle}: {e}")

    return total_saved

def rank_photo(metadata):
    score = 0
    if metadata.get("solo"):
        score += 30
    if metadata.get("face_visible"):
        score += 20
    if metadata.get("photoshoot"):
        score += 15
    if metadata.get("high_quality"):
        score += 15
    if metadata.get("engagement"):
        score += 20
    return score

def analyze_metadata_for_discovery(item, custom_prompt=None):
    """Uses Gemini to extract ranking metadata from search snippets."""
    base_prompt = custom_prompt if custom_prompt else "Analyze this search result for a celebrity fanpage post."
    prompt = f"""
    {base_prompt}
    
    Metadata:
    Title: {item.get('title')}
    Snippet: {item.get('snippet')}
    
    Task: Detect if this content is:
    - solo: a single person is the focus
    - face_visible: face is clearly visible
    - photoshoot: professionally shot
    - high_quality: resolution/aesthetic is high
    - engagement: likely high engagement based on source or keywords
    
    Return JSON only:
    {{
      "solo": boolean,
      "face_visible": boolean,
      "photoshoot": boolean,
      "high_quality": boolean,
      "engagement": boolean
    }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        return clean_gemini_json(response.text)
    except:
        return {"solo": False, "face_visible": False, "photoshoot": False, "high_quality": False, "engagement": False}

def build_discovery_queries(handle, deep_mode="hidden_gems"):
    handle = handle.replace("@", "").strip()

    actor = "Gayatri Bhardwaj"

    if deep_mode == "hidden_gems":

        return [

            # Pinterest
            f'"{actor}" site:pinterest.com',

            # Instagram posts
            f'"{actor}" site:instagram.com/p',

            # Fanpages
            f'"{actor}" fanpage',
            f'"{actor}" aesthetic fanpage',

            # Rare content
            f'"{actor}" unseen photos',
            f'"{actor}" candid photos',
            f'"{actor}" old photoshoot',
            f'"{actor}" behind the scenes',
            f'"{actor}" fashion week',
            f'"{actor}" airport look',
            f'"{actor}" magazine',
            f'"{actor}" event',

            # Randomize results
            f'"{actor}" photos {random.randint(1,10000)}'
        ]

    elif deep_mode == "bold":

        return [

            f'"{actor}" glamour photoshoot',
            f'"{actor}" event look',
            f'"{actor}" beach look',
            f'"{actor}" stylish look',
            f'"{actor}" magazine shoot',

            f'"{actor}" photos {random.randint(1,10000)}'
        ]

    else:

        return [

            f'"{actor}" actress photos',
            f'"{actor}" solo photos',
            f'"{actor}" instagram photos',

            f'"{actor}" photos {random.randint(1,10000)}'
        ]

def deep_discovery_ai(handles, deep_mode="hidden_gems", limit=10, custom_prompt=None, discovery_engine="google_images"):
    """Searches multiple sources, ranks results via AI, and sends top picks."""
    serp_api_key = os.getenv("SERP_API_KEY")
    if not serp_api_key:
        raise Exception("SERP_API_KEY missing in .env")

    discovery_results = []
    seen = set()

    for handle in handles:
        queries = build_discovery_queries(handle, deep_mode)
        for query in queries:
            search = GoogleSearch({
                "q": query,
                "api_key": serp_api_key,
                "num": 10
            })
            results = search.get_dict()
            organic = results.get("organic_results", [])

            for item in organic:
                url = item.get("link", "")
                if not url: continue
                
                shortcode = extract_shortcode(url) if "instagram.com" in url else url
                if shortcode in seen: continue
                seen.add(shortcode)

                metadata = analyze_metadata_for_discovery(item, custom_prompt)
                score = rank_photo(metadata)
                
                discovery_results.append({
                    "url": url,
                    "score": score,
                    "metadata": metadata
                })

    # Sort by discovery score
    discovery_results.sort(key=lambda x: x["score"], reverse=True)
    
    sent = 0
    failed = 0
    for entry in discovery_results[:limit]:
        url = entry["url"]
        try:
            if "instagram.com" not in url: continue # instaloader requirement
            image_paths = download_photo_post(url)
            caption = f"🌌 Deep Discovery AI Pick\n\nRank Score: {entry['score']}/100\n\nSource: {url}"
            send_carousel_to_telegram(image_paths, caption, url)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"Discovery failed for {url}: {e}")

    return f"Deep Discovery AI completed. Sent {sent} top-ranked photos. Failed: {failed}"

def build_deep_search_queries(handle, deep_mode):
    name = handle.replace("@", "").strip()

    queries = {
        "Hidden Gems": [
            f'"Gayatri Bhardwaj" rare photos',
            f'"Gayatri Bhardwaj" unseen photos',
            f'"Gayatri Bhardwaj" candid photos',
            f'"{name}" "Gayatri Bhardwaj" photoshoot',
            f'site:instagram.com/p "{name}"'
        ],

        "Photoshoots": [
            f'"Gayatri Bhardwaj" photoshoot',
            f'"Gayatri Bhardwaj" fashion shoot',
            f'"Gayatri Bhardwaj" magazine',
            f'site:instagram.com/p "{name}" photoshoot'
        ],

        "Candid Looks": [
            f'"Gayatri Bhardwaj" candid',
            f'"Gayatri Bhardwaj" airport look',
            f'"Gayatri Bhardwaj" event candid',
            f'site:instagram.com/p "{name}" candid'
        ],

        "Event Looks": [
            f'"Gayatri Bhardwaj" event',
            f'"Gayatri Bhardwaj" red carpet',
            f'"Gayatri Bhardwaj" award show',
            f'site:instagram.com/p "{name}" event'
        ],

        "High Reach Looks": [
            f'"Gayatri Bhardwaj" hot photoshoot',
            f'"Gayatri Bhardwaj" glamorous look',
            f'"Gayatri Bhardwaj" stylish look',
            f'"Gayatri Bhardwaj" viral photo',
            f'site:instagram.com/p "{name}" stunning'
        ]
    }

    return queries.get(deep_mode, queries["Hidden Gems"])

def deep_search_and_send(handles, deep_mode, limit=10):
    SERP_API_KEY = os.getenv("SERP_API_KEY")

    if not SERP_API_KEY:
        raise Exception("SERP_API_KEY missing")

    found_urls = []
    seen = set()

    for handle in handles:
        queries = build_deep_search_queries(handle, deep_mode)

        for query in queries:
            search = GoogleSearch({
                "q": query,
                "api_key": SERP_API_KEY,
                "num": 10
            })

            results = search.get_dict()
            organic = results.get("organic_results", [])

            for item in organic:
                url = item.get("link", "")

                if "instagram.com/p/" not in url:
                    continue

                shortcode = extract_shortcode(url)

                if shortcode in seen:
                    continue

                seen.add(shortcode)
                found_urls.append(url)

                if len(found_urls) >= limit:
                    break

            if len(found_urls) >= limit:
                break

    sent = 0
    failed = 0

    for url in found_urls[:limit]:
        try:
            image_paths = download_photo_post(url)

            caption = f"""
🌸 Deep Search Pick

Mode: {deep_mode}

Source:
{url}
"""

            send_carousel_to_telegram(
                image_paths=image_paths,
                caption=caption,
                source_url=url
            )

            sent += 1

        except Exception as e:
            failed += 1

            send_message_to_telegram(
                f"""
⚠️ Deep Search Download Failed

Mode: {deep_mode}

Source:
{url}

Reason:
{e}
"""
            )

    return f"Deep search completed. Sent: {sent}, Failed: {failed}"


# -------------------------
# PROCESS POST
# -------------------------

def process_post(post_id, handle, shortcode, url, post_type, content_mode, style):
    # Pull pre-generated Gemini caption
    caption = get_gemini_caption_from_db(post_id)

    try:
        if post_type == "reel":
            message = f"""
🎬 Reel Found

Handle: @{handle}
Link: {url}
Analysis & Captions:
{caption}
"""
            send_message_to_telegram(message)
            update_status(post_id, "REEL_LINK_SENT", caption)
            return "Reel link sent to Telegram"

        if post_type == "photo":
            image_paths = download_photo_post(url)
            sent_count = send_carousel_to_telegram(
                image_paths=image_paths,
                caption=caption,
                source_url=url
            )
            update_status(post_id, f"PHOTO_SENT_{sent_count}", caption)
            return f"{sent_count} unique photo(s) sent to Telegram."

        message = f"""
⚠️ Unknown Post Type

Handle: @{handle}
Link: {url}

Caption idea:
{caption}
"""
        send_message_to_telegram(message)
        update_status(post_id, "UNKNOWN_LINK_SENT", caption)
        return "Unknown type. Source link sent."

    except Exception as e:
        fallback_message = f"""
⚠️ Photo Download Failed

Handle: @{handle}
Source: {url}

Reason:
{str(e)}

Caption idea:
{caption}
"""
        send_message_to_telegram(fallback_message)
        update_status(post_id, "DOWNLOAD_FAILED_LINK_SENT", caption)
        return "Download failed. Source link sent to Telegram instead."
