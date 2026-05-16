import glob
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import requests
import google.generativeai as genai

INDIA_TOP_STORIES_RSS = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
GLOBAL_TOP_STORIES_RSS = "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

def clean_html(text):
    if not text: return ""
    return re.sub(r"<[^>]+>", "", text).strip()

def get_user_reports():
    reports = []
    if not os.path.exists("reports"): return reports
    
    # SORT BY NEWEST FILE FIRST
    report_files = glob.glob("reports/*.txt")
    report_files.sort(key=os.path.getmtime, reverse=True) 

    for file_path in report_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()
            lines = content.split("\n", 1)
            reports.append({
                "type": "report",
                "title": lines[0].strip() if lines and lines[0].strip() else "Untitled Report",
                "body": lines[1].strip() if len(lines) > 1 else "",
            })
        except Exception as error:
            print(f"Error reading report {file_path}: {error}")
    return reports

def analyze_with_ai(title, summary):
    fallback = {"bias": "Pending AI Analysis.", "sources": "Original publisher.", "effect": "Impact being calculated."}
    if not model: return fallback
    
    prompt = f"""
    You are an unbiased, highly objective intelligence analyst. Analyze this news briefly:
    Title: {title}
    Summary: {summary}
    Provide a JSON response strictly with these 3 keys:
    "bias": (1 short sentence on potential political, corporate, or media bias)
    "sources": (1 short sentence on what entities or data are likely cited)
    "effect": (1 short sentence on how this impacts the general public)
    Only return valid JSON, no markdown formatting.
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"AI Error for '{title}': {e}")
        return fallback

def parse_rss_items(feed_xml, region, max_items):
    root = ET.fromstring(feed_xml)
    items = []
    seen_titles = set()

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("source") or "Unknown Source").strip()
        description = clean_html(item.findtext("description") or "")
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        published_iso = parsedate_to_datetime(pub_date_raw).isoformat() if pub_date_raw else pub_date_raw

        if not title or not link or title in seen_titles: continue
        seen_titles.add(title)

        print(f"Analyzing: {title[:30]}...")
        ai_data = analyze_with_ai(title, description)
        time.sleep(2) 

        items.append({
            "type": "news",
            "region": region,
            "title": title,
            "source": source,
            "published": published_iso,
            "summary": description,
            "link": link,
            "bias": ai_data.get("bias", "Neutral"),
            "sources": ai_data.get("sources", "Multiple"),
            "effect": ai_data.get("effect", "Ongoing")
        })

        if len(items) >= max_items: break
    return items

def fetch_rss(url, region, max_items):
    print(f"Fetching {region} headlines...")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return parse_rss_items(response.text, region, max_items)

if __name__ == "__main__":
    print("Gathering reports...")
    user_reports = get_user_reports()
    try:
        india_news = fetch_rss(INDIA_TOP_STORIES_RSS, "india", 20)
        global_news = fetch_rss(GLOBAL_TOP_STORIES_RSS, "global", 10)
    except Exception as error:
        print(f"News fetch error: {error}")
        india_news, global_news = [], []

    final_data = user_reports + india_news + global_news
    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(final_data, file, ensure_ascii=False, indent=2)
    print("Done! Data saved.")
