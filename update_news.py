import glob
import json
import os
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

INDIA_TOP_STORIES_RSS = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
GLOBAL_TOP_STORIES_RSS = (
    "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en"
)


def clean_html(text):
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def get_user_reports():
    reports = []
    if not os.path.exists("reports"):
        os.makedirs("reports")

    for file_path in sorted(glob.glob("reports/*.txt")):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()
            lines = content.split("\n", 1)
            reports.append(
                {
                    "type": "report",
                    "title": lines[0].strip() if lines and lines[0].strip() else "Untitled Report",
                    "body": lines[1].strip() if len(lines) > 1 else "",
                }
            )
        except Exception as error:
            print(f"Error reading report {file_path}: {error}")

    return reports


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
        published_iso = ""
        if pub_date_raw:
            try:
                published_iso = parsedate_to_datetime(pub_date_raw).isoformat()
            except Exception:
                published_iso = pub_date_raw

        if not title or not link:
            continue
        if title in seen_titles:
            continue

        seen_titles.add(title)
        items.append(
            {
                "type": "news",
                "region": region,
                "title": title,
                "source": source,
                "published": published_iso,
                "summary": description,
                "link": link,
            }
        )

        if len(items) >= max_items:
            break

    return items


def fetch_rss(url, region, max_items):
    print(f"Fetching {region} headlines...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return parse_rss_items(response.text, region, max_items)


def get_latest_news():
    india_news = fetch_rss(INDIA_TOP_STORIES_RSS, "india", 20)
    global_news = fetch_rss(GLOBAL_TOP_STORIES_RSS, "global", 10)
    return india_news, global_news


if __name__ == "__main__":
    print("Gathering data...")

    user_reports = get_user_reports()

    try:
        india_news, global_news = get_latest_news()
    except Exception as error:
        print(f"News fetch error: {error}")
        india_news = [
            {
                "type": "news",
                "region": "india",
                "title": "System Alert: India feed unavailable",
                "source": "System",
                "published": "",
                "summary": str(error),
                "link": "#",
            }
        ]
        global_news = [
            {
                "type": "news",
                "region": "global",
                "title": "System Alert: Global feed unavailable",
                "source": "System",
                "published": "",
                "summary": str(error),
                "link": "#",
            }
        ]

    final_data = user_reports + india_news + global_news

    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(final_data, file, ensure_ascii=False, indent=2)

    print(
        f"Successfully wrote {len(final_data)} items "
        f"({len(user_reports)} reports, {len(india_news)} India, {len(global_news)} global)."
    )
