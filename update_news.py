import os
import requests
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types
import sys
import glob
import json
import time

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: GEMINI_API_KEY is missing.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

def get_user_reports():
    reports = []
    if not os.path.exists('reports'):
        os.makedirs('reports')
    for file_path in glob.glob('reports/*.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n', 1)
            reports.append({
                "type": "report",
                "title": lines[0].strip() if len(lines) > 0 else "Untitled Report",
                "body": lines[1].strip() if len(lines) > 1 else ""
            })
        except Exception as e:
            print(f"Error reading report: {e}")
    return reports

def get_latest_news():
    print("Fetching Google News...")
    url = "https://news.google.com/rss?gl=IN&ceid=IN:en"
    # Using a heavier User-Agent so Google doesn't block the connection
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        articles = [{'title': item.find('title').text, 'link': item.find('link').text} for item in root.findall('.//item')[:12]]
        print(f"Successfully grabbed {len(articles)} articles from RSS.")
        return articles
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def generate_all_news(articles):
    if not articles: return []
    articles_text = "\n".join([f"Title: {a['title']} | Link: {a['link']}" for a in articles])
    
    prompt = f"""
    Analyze these {len(articles)} news headlines. Return ONLY a valid JSON array.
    Each object in the array MUST have these exact keys:
    "title" (string), "summary" (string, 3 paragraphs separated by <br><br>), "analysis" (string), "bias" (string), "score" (integer 1-100), and "link" (string).
    Articles:
    {articles_text}
    """
    
    # The crucial Retry Logic is back
    max_retries = 4
    for attempt in range(max_retries):
        try:
            print(f"Asking AI to process data (Attempt {attempt+1} of {max_retries})...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            for item in data:
                item["type"] = "news"
            print("AI processing successful!")
            return data
            
        except Exception as e:
            print(f"Server busy or AI Error: {e}")
            if attempt < max_retries - 1:
                print("Waiting 10 seconds to let the server cool down...")
                time.sleep(10)
            else:
                print("FATAL: AI failed after all retries.")
                return []

if __name__ == "__main__":
    print("Gathering data...")
    user_reports = get_user_reports()
    articles = get_latest_news()
    ai_news = generate_all_news(articles)
    
    final_data = user_reports + ai_news
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully wrote {len(final_data)} items to data.json")
