import hashlib
import os
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
import google.generativeai as genai
from groq import Groq
from PIL import Image, ImageStat
from io import BytesIO
import uuid

load_dotenv()

DB_PATH = "fanpage_data.db"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Instaloader once for reuse
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.google.com/"
}

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
        return True, "Skipped: file missing"
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        if w < 250 or h < 250:
            return False, "Image too small"
        # Use pixel variance as blur proxy
        stat = ImageStat.Stat(img.convert("L"))
        if stat.var[0] < 200:
            return False, f"Too blurry: var={stat.var[0]:.1f}"
        return True, f"Passed. Size: {w}x{h}"
    except Exception as e:
        return False, f"Read error: {e}"

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


def _download_image_url(img_url, folder="downloads/photos"):
    """Downloads a single image URL to disk, returns local path."""
    os.makedirs(folder, exist_ok=True)
    resp = requests.get(img_url, headers=DOWNLOAD_HEADERS, timeout=30)
    if resp.status_code != 200:
        raise ValueError(f"HTTP {resp.status_code} for {img_url}")
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    if img.width < 200 or img.height < 200:
        raise ValueError("Image too small, skipping")
    out = os.path.join(folder, f"{uuid.uuid4().hex[:10]}.jpg")
    img.save(out, "JPEG", quality=92)
    return out


def download_photo_post(url):
    """
    Downloads photos for an Instagram post URL.
    Strategy chain:
      1. RapidAPI Instagram Scraper (most reliable, free tier 100 req/month)
      2. Instagram oEmbed thumbnail
      3. If all fail - raise with helpful message to send link instead
    """
    os.makedirs("downloads/photos", exist_ok=True)
    shortcode = extract_shortcode(url)
    image_paths = []

    # ── Strategy 1: RapidAPI subscribed APIs ──
    rapid_key = os.getenv("RAPIDAPI_KEY")
    if rapid_key:
        # API 1: Instagram best experience by Lobster
        try:
            resp = requests.get(
                "https://instagram-best-experience.p.rapidapi.com/media",
                headers={
                    "x-rapidapi-key": rapid_key,
                    "x-rapidapi-host": "instagram-best-experience.p.rapidapi.com"
                },
                params={"url": url},
                timeout=20
            )
            print(f"Lobster status: {resp.status_code}, response: {resp.text[:300]}")
            if resp.status_code == 200:
                data = resp.json()
                # Flatten all image URLs from any response shape
                candidates = []
                def _extract_urls(obj):
                    if isinstance(obj, str) and obj.startswith("http"):
                        candidates.append(obj)
                    elif isinstance(obj, list):
                        for x in obj: _extract_urls(x)
                    elif isinstance(obj, dict):
                        for k, v in obj.items():
                            if any(x in k.lower() for x in ["url", "image", "display", "thumb"]):
                                _extract_urls(v)
                _extract_urls(data)
                for img_url in candidates[:6]:
                    if not any(x in img_url for x in [".jpg", ".jpeg", ".png", ".webp"]):
                        continue
                    try:
                        path = _download_image_url(img_url)
                        image_paths.append(path)
                    except Exception as e:
                        print(f"Lobster img dl failed: {e}")
        except Exception as e:
            print(f"Lobster API failed: {e}")

        # API 2: Instagram Scraper Stable API by RockSolid
        if not image_paths:
            try:
                resp = requests.get(
                    "https://instagram-scraper-stable-api.p.rapidapi.com/ig/post_info/",
                    headers={
                        "x-rapidapi-key": rapid_key,
                        "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
                    },
                    params={"url": url},
                    timeout=25
                )
                print(f"RockSolid status: {resp.status_code}, response: {resp.text[:300]}")
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = []
                    def _extract_urls2(obj):
                        if isinstance(obj, str) and obj.startswith("http"):
                            candidates.append(obj)
                        elif isinstance(obj, list):
                            for x in obj: _extract_urls2(x)
                        elif isinstance(obj, dict):
                            for k, v in obj.items():
                                if any(x in k.lower() for x in ["url", "image", "display", "thumb"]):
                                    _extract_urls2(v)
                    _extract_urls2(data)
                    for img_url in candidates[:6]:
                        if not any(x in img_url for x in [".jpg", ".jpeg", ".png", ".webp"]):
                            continue
                        try:
                            path = _download_image_url(img_url)
                            image_paths.append(path)
                        except Exception as e:
                            print(f"RockSolid img dl failed: {e}")
            except Exception as e:
                print(f"RockSolid API failed: {e}")

    # ── Strategy 2: oEmbed thumbnail ──
    if not image_paths:
        try:
            oembed = requests.get(
                f"https://www.instagram.com/oembed/?url={url}",
                headers=DOWNLOAD_HEADERS,
                timeout=15
            )
            if oembed.status_code == 200:
                thumb = oembed.json().get("thumbnail_url")
                if thumb:
                    path = _download_image_url(thumb)
                    image_paths.append(path)
        except Exception as e:
            print(f"oEmbed failed: {e}")

    image_paths = remove_duplicate_images(image_paths)

    if not image_paths:
        raise ValueError(
            f"Could not download images from {url}\n"
            "Check Streamlit logs for API debug output. "
            "Make sure RAPIDAPI_KEY is set in Streamlit Secrets."
        )

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
# NEW FEATURE ENGINES
# -------------------------

def generate_caption_variants(topic, style, count=5):
    """Generate caption variants for a given topic using Gemini."""
    prompt = f"""
You are a creative Instagram fanpage content writer for Gayatri Bhardwaj.

Generate {count} UNIQUE, trendy, aesthetic Instagram captions for this topic: "{topic}"
Style: {style}

Rules:
- Each caption must be different in tone and structure
- Keep each under 150 characters
- Include 1-2 relevant emojis per caption
- No hashtags inside captions
- Avoid cringe or generic lines

Return JSON only:
{{
  "captions": ["caption1", "caption2", "caption3", "caption4", "caption5"]
}}
"""
    try:
        response = gemini_model.generate_content(prompt)
        result = clean_gemini_json(response.text)
        return result.get("captions", [])
    except Exception as e:
        print(f"Caption variants failed: {e}")
        return [generate_caption(style, "Photo Posts") for _ in range(count)]


def generate_hashtag_pack(topic, niche="actress fanpage"):
    """Generate a hashtag pack using Gemini."""
    prompt = f"""
Generate a high-reach Instagram hashtag pack for:
Topic: {topic}
Niche: {niche}

Return 30 hashtags grouped as:
- 10 mega hashtags (10M+ posts)
- 10 mid hashtags (500K-5M posts)
- 10 niche hashtags (under 500K posts)

Return JSON only:
{{
  "mega": ["#tag1", ...],
  "mid": ["#tag1", ...],
  "niche": ["#tag1", ...]
}}
"""
    try:
        response = gemini_model.generate_content(prompt)
        return clean_gemini_json(response.text)
    except Exception as e:
        print(f"Hashtag pack failed: {e}")
        return {"mega": [], "mid": [], "niche": []}


def get_best_posting_times():
    """Returns best posting times for Instagram fanpages."""
    return [
        {"day": "Monday",    "time": "7:00 PM", "reason": "Post-work scroll peak"},
        {"day": "Tuesday",   "time": "8:00 AM", "reason": "Morning commute"},
        {"day": "Wednesday", "time": "11:00 AM", "reason": "Midweek lunch break"},
        {"day": "Thursday",  "time": "7:00 PM", "reason": "Pre-weekend energy"},
        {"day": "Friday",    "time": "12:00 PM", "reason": "TGIF engagement spike"},
        {"day": "Saturday",  "time": "10:00 AM", "reason": "Weekend morning browse"},
        {"day": "Sunday",    "time": "6:00 PM",  "reason": "Sunday evening peak"},
    ]


def add_watermark(image_path, watermark_text="@gayatribhardwaj__"):
    """Adds a subtle text watermark to an image. Returns new file path."""
    from PIL import ImageDraw, ImageFont
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(20, w // 30)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = w - tw - 20, h - th - 20

    draw.text((x + 1, y + 1), watermark_text, font=font, fill=(0, 0, 0, 80))
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 160))

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    out_path = image_path.replace(".jpg", "_wm.jpg").replace(".png", "_wm.jpg")
    combined.save(out_path, "JPEG", quality=92)
    return out_path


def get_content_log():
    """Returns all sent posts for content calendar view."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT handle, shortcode, url, post_type, status, viral_score, gemini_caption, created_at
        FROM posts
        WHERE status NOT IN ('PENDING', 'SKIPPED')
        ORDER BY created_at DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    return rows


# -------------------------
# CREATIVE EDIT FEATURES
# -------------------------

def make_collage(image_paths, layout="2x2", title_text=""):
    """
    Creates a photo collage from a list of image paths.
    layout options: '2x2', '3x1', '1x3', '2x3'
    Returns output file path.
    """
    from PIL import ImageDraw, ImageFont

    layout_map = {
        "2x2": (2, 2), "3x1": (1, 3), "1x3": (3, 1),
        "2x3": (2, 3), "3x2": (3, 2)
    }
    cols, rows = layout_map.get(layout, (2, 2))
    needed = cols * rows
    paths = (image_paths * (needed // len(image_paths) + 1))[:needed]

    cell_w, cell_h = 600, 600
    padding = 8
    header_h = 60 if title_text else 0
    canvas_w = cols * cell_w + (cols + 1) * padding
    canvas_h = rows * cell_h + (rows + 1) * padding + header_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 240, 248))
    draw = ImageDraw.Draw(canvas)

    if title_text:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except Exception:
            font = ImageFont.load_default()
        draw.text((canvas_w // 2 - 100, 14), title_text, fill=(180, 50, 100), font=font)

    for idx, path in enumerate(paths):
        row_idx = idx // cols
        col_idx = idx % cols
        x = padding + col_idx * (cell_w + padding)
        y = header_h + padding + row_idx * (cell_h + padding)
        try:
            img = Image.open(path).convert("RGB")
            img = img.resize((cell_w, cell_h), Image.LANCZOS)
            canvas.paste(img, (x, y))
        except Exception:
            pass

    os.makedirs("downloads/collages", exist_ok=True)
    out = f"downloads/collages/collage_{uuid.uuid4().hex[:8]}.jpg"
    canvas.save(out, "JPEG", quality=92)
    return out


STYLE_PRESETS = {
    "Cinematic Golden Hour": {
        "brightness": 1.15, "contrast": 1.2, "saturation": 0.85,
        "tint": (255, 220, 150, 35)
    },
    "Soft Aesthetic": {
        "brightness": 1.2, "contrast": 0.9, "saturation": 0.7,
        "tint": (255, 230, 240, 40)
    },
    "Moody Dark": {
        "brightness": 0.82, "contrast": 1.35, "saturation": 0.6,
        "tint": (20, 10, 40, 50)
    },
    "Vintage Film": {
        "brightness": 1.05, "contrast": 1.1, "saturation": 0.65,
        "tint": (200, 170, 120, 45)
    },
    "Neon Pop": {
        "brightness": 1.1, "contrast": 1.3, "saturation": 1.6,
        "tint": (200, 50, 200, 20)
    },
    "Clean White": {
        "brightness": 1.3, "contrast": 0.95, "saturation": 0.8,
        "tint": (255, 255, 255, 30)
    },
}


def apply_style_filter(image_path, preset_name):
    """
    Applies a cinematic/aesthetic filter preset using Pillow only.
    Returns output file path.
    """
    from PIL import ImageEnhance

    preset = STYLE_PRESETS.get(preset_name, STYLE_PRESETS["Cinematic Golden Hour"])
    img = Image.open(image_path).convert("RGB")

    img = ImageEnhance.Brightness(img).enhance(preset["brightness"])
    img = ImageEnhance.Contrast(img).enhance(preset["contrast"])
    img = ImageEnhance.Color(img).enhance(preset["saturation"])

    tint_layer = Image.new("RGBA", img.size, preset["tint"])
    img = Image.alpha_composite(img.convert("RGBA"), tint_layer).convert("RGB")

    os.makedirs("downloads/edits", exist_ok=True)
    slug = preset_name.lower().replace(" ", "_")
    out = f"downloads/edits/{slug}_{uuid.uuid4().hex[:6]}.jpg"
    img.save(out, "JPEG", quality=92)
    return out


def ai_style_edit(image_path, prompt, strength=0.65):
    """
    Sends image to Stability AI img2img for AI-powered style transformation.
    Requires STABILITY_API_KEY in .env (free tier: 25 credits/month).
    Falls back to local filter if key missing.
    """
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        return apply_style_filter(image_path, "Cinematic Golden Hour"), "No Stability key — applied local filter instead."

    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    # Stability requires dimensions multiple of 64, max 1024
    new_w = min(1024, (w // 64) * 64)
    new_h = min(1024, (h // 64) * 64)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = requests.post(
        "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        files={"init_image": ("image.png", buf, "image/png")},
        data={
            "text_prompts[0][text]": prompt,
            "text_prompts[0][weight]": "1",
            "init_image_strength": str(1 - strength),
            "cfg_scale": "7",
            "samples": "1",
            "steps": "30",
        },
        timeout=120
    )

    if response.status_code != 200:
        return apply_style_filter(image_path, "Cinematic Golden Hour"), f"API error {response.status_code} — used local filter."

    data = response.json()
    img_b64 = data["artifacts"][0]["base64"]
    import base64
    out_img = Image.open(BytesIO(base64.b64decode(img_b64)))
    os.makedirs("downloads/ai_edits", exist_ok=True)
    out_path = f"downloads/ai_edits/ai_edit_{uuid.uuid4().hex[:8]}.jpg"
    out_img.save(out_path, "JPEG", quality=92)
    return out_path, "AI edit complete via Stability AI."


def costume_transfer(person_path, costume_path, strength=0.70):
    """
    Step 1: Gemini Vision reads the costume image and generates a detailed fashion prompt.
    Step 2: Stability AI img2img applies that costume style onto the person photo.
    Falls back to local filter if Stability key missing.
    """
    # --- Step 1: Gemini reads costume ---
    try:
        costume_img = Image.open(costume_path).convert("RGB")
        vision_prompt = """
You are a fashion analyst. Describe this outfit/costume in extreme detail for an AI image generation prompt.
Focus on: fabric, color, style, cut, neckline, sleeves, embroidery, accessories, occasion.
Do NOT mention the person wearing it. Only describe the garment.
Return a single detailed comma-separated prompt string. No JSON, no bullet points."""
        response = gemini_model.generate_content([
            vision_prompt,
            costume_img
        ])
        costume_description = response.text.strip()
    except Exception as e:
        costume_description = "elegant traditional Indian outfit, detailed embroidery, rich fabric"
        print(f"Gemini vision failed: {e}")

    full_prompt = (
        f"Fashion editorial photo, same person, same face, same pose, "
        f"now wearing: {costume_description}, "
        f"professional photography, soft studio lighting, high resolution, 8k"
    )

    # --- Step 2: Stability img2img ---
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        out = apply_style_filter(person_path, "Soft Aesthetic")
        return out, f"No Stability key. Costume detected: {costume_description[:120]}..."

    img = Image.open(person_path).convert("RGB")
    w, h = img.size
    new_w = min(1024, (w // 64) * 64)
    new_h = min(1024, (h // 64) * 64)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = requests.post(
        "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        files={"init_image": ("image.png", buf, "image/png")},
        data={
            "text_prompts[0][text]": full_prompt,
            "text_prompts[0][weight]": "1",
            "init_image_strength": str(1 - strength),
            "cfg_scale": "8",
            "samples": "1",
            "steps": "35",
        },
        timeout=120
    )

    if resp.status_code != 200:
        out = apply_style_filter(person_path, "Soft Aesthetic")
        return out, f"Stability error {resp.status_code}. Costume: {costume_description[:100]}"

    import base64
    img_b64 = resp.json()["artifacts"][0]["base64"]
    out_img = Image.open(BytesIO(base64.b64decode(img_b64)))
    os.makedirs("downloads/costume_edits", exist_ok=True)
    out_path = f"downloads/costume_edits/costume_{uuid.uuid4().hex[:8]}.jpg"
    out_img.save(out_path, "JPEG", quality=92)
    return out_path, f"Costume applied! Detected: {costume_description[:150]}"


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
