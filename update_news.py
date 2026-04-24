import os
import re
import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai
import sys

# 1. Verify API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: GEMINI_API_KEY is missing. Please check your GitHub Secrets.")
    sys.exit(1)

# Configure the AI
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_latest_news():
    print("Fetching news from Google RSS...")
    url = "https://news.google.com/rss?gl=IN&ceid=IN:en"
    # Pretend to be a normal web browser so Google doesn't block the request
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
        
        try:
            response = model.generate_content(prompt)
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
            
        except Exception as e:
            print(f"Skipping article due to AI error: {e}")
            continue
            
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
