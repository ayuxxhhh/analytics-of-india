import os
import re
import requests
import xml.etree.ElementTree as ET
from google import genai
import sys
import time

# 1. Verify API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: GEMINI_API_KEY is missing. Please check your GitHub Secrets.")
    sys.exit(1)

# Configure the AI using the new SDK
client = genai.Client(api_key=api_key)

def get_latest_news():
    print("Fetching news from Google RSS...")
    url = "https://news.google.com/rss?gl=IN&ceid=IN:en"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        articles = []
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text
            articles.append(title)
            
        if not articles:
            print("Warning: No articles were found in the RSS feed.")
            
        return articles
    except Exception as e:
        print(f"Error fetching news: {e}")
        sys.exit(1)

def generate_neutral_content(articles):
    html_cards = ""
    
    for article in articles:
        print(f"Processing: {article[:30]}...")
        prompt = f"""
        Act as a strictly neutral, highly professional news analyst. 
        Take this news headline/topic: "{article}"
        Write a short, 2-sentence summary of the facts. 
        Strip away all political bias, sensationalism, and emotion. 
        Return the output in this EXACT format (no markdown formatting, no extra words):
        Title: [Neutral Title]
        Summary: [2-sentence factual summary]
        """
        
        # Retry Logic added here
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                text = response.text
                
                lines = text.split('\n')
                title = lines[0].replace('Title: ', '').strip()
                summary = lines[1].replace('Summary: ', '').strip()
                
                card_html = f"""
        <div class="news-card">
            <span class="tag">LATEST BRIEFING</span>
            <h2>{title}</h2>
            <p>{summary}</p>
        </div>"""
                html_cards += card_html
                break # Success! Break out of the retry loop.
                
            except Exception as e:
                if "503" in str(e) or "429" in str(e):
                    print(f"Server busy. Retrying in 5 seconds... (Attempt {attempt + 1} of {max_retries})")
                    time.sleep(5) # Wait 5 seconds before trying again
                else:
                    print(f"Skipping article due to AI error: {e}")
                    break # Not a traffic issue, skip to the next article
        
        # Polite pause between articles so we don't overwhelm the free server
        time.sleep(2) 
            
    return html_cards

def update_html(new_content):
    if not new_content.strip():
        print("No new content generated. Aborting HTML update so the site doesn't go blank.")
        sys.exit(1)
        
    print("Reading index.html...")
    with open('index.html', 'r', encoding='utf-8') as file:
        html = file.read()
        
    pattern = r'(<section class="news-grid" id="news-container">)(.*?)(</section>)'
    updated_html = re.sub(pattern, r'\1\n' + new_content + r'\n\3', html, flags=re.DOTALL)
    
    print("Writing updated index.html...")
    with open('index.html', 'w', encoding='utf-8') as file:
        file.write(updated_html)

if __name__ == "__main__":
    news_items = get_latest_news()
    new_html_content = generate_neutral_content(news_items)
    update_html(new_html_content)
    print("Script completed successfully!")
