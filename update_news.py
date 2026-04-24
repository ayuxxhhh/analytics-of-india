import os
import re
import requests
import xml.etree.ElementTree as ET
from google import genai
import sys
import time
import glob
import json

# Verify API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: GEMINI_API_KEY is missing.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

def get_user_reports():
    print("Checking backend for original editorial reports...")
    reports_html = ""
    
    if not os.path.exists('reports'):
        os.makedirs('reports')
        return reports_html

    report_files = glob.glob('reports/*.txt')
    for file_path in report_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n', 1)
            title = lines[0].strip() if len(lines) > 0 else "Untitled Report"
            body = lines[1].strip() if len(lines) > 1 else ""
            
            card_html = f"""
        <div class="news-card" style="border-color: var(--accent); background: rgba(255, 74, 90, 0.05);">
            <span class="tag" style="color: #fff; background: var(--accent); padding: 4px 8px; border-radius: 4px; font-weight: bold;">ORIGINAL REPORT</span>
            <h2>{title}</h2>
            <div style="color: var(--text-muted); line-height: 1.6; margin-top: 1rem; white-space: pre-wrap;">{body}</div>
        </div>"""
            reports_html += card_html
        except Exception as e:
            print(f"Error reading report {file_path}: {e}")
            
    return reports_html

def get_latest_news():
    print("Fetching expanded news roster and source links...")
    url = "https://news.google.com/rss?gl=IN&ceid=IN:en"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        articles = []
        for item in root.findall('.//item')[:15]:
            title = item.find('title').text
            link = item.find('link').text
            articles.append({'title': title, 'link': link})
            
        return articles
    except Exception as e:
        print(f"Error fetching news: {e}")
        sys.exit(1)

def generate_neutral_content(articles):
    html_cards = ""
    max_retries = 3
    
    for article in articles:
        print(f"Drafting full analysis for: {article['title'][:30]}...")
        
        prompt = f"""
        Act as a strictly neutral, highly professional data and news analyst. 
        Take this news headline: "{article['title']}"
        
        You MUST return the output ONLY as a valid JSON object. Do not add any conversational text.
        Use these exact keys:
        {{
            "title": "A neutral, factual title",
            "summary": "3 paragraphs of factual reporting, separated by HTML <br><br> tags",
            "analysis": "1 paragraph analyzing the broader implications or context",
            "bias": "1 paragraph explaining the potential biases in mainstream reporting",
            "score": a single integer from 1 to 100 representing sensationalism risk
        }}
        """
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                text = response.text
                
                # The Bulletproof JSON Vacuum: Only grab what is between { and }
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if not json_match:
                    raise ValueError(f"No JSON formatting found in AI response.")
                    
                data = json.loads(json_match.group(0))
                
                # Using .get() prevents crashes if the AI accidentally renames a key
                title = data.get('title', 'News Update')
                summary = data.get('summary', 'Summary processing failed.')
                analysis = data.get('analysis', 'Analysis processing failed.')
                bias = data.get('bias', 'Bias processing failed.')
                
                # Safely convert score to integer
                try:
                    score = int(data.get('score', 50))
                except ValueError:
                    score = 50
                
                bar_color = "#ff4a5a" 
                if score < 40:
                    bar_color = "#4CAF50" 
                elif score < 70:
                    bar_color = "#FFC107" 
                
                card_html = f"""
        <div class="news-card">
            <span class="tag">ANALYTICS ENGINE</span>
            <h2>{title}</h2>
            
            <div style="margin: 1.5rem 0; padding-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 5px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">
                    <span>Media Sensationalism Risk</span>
                    <span>{score}/100</span>
                </div>
                <div style="width: 100%; background: #1a1a1a; height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="width: {score}%; background: {bar_color}; height: 100%;"></div>
                </div>
            </div>

            <div style="color: var(--text-main); line-height: 1.7;">{summary}</div>
            
            <div style="background: rgba(255,255,255,0.02); padding: 1.5rem; border-radius: 8px; border-left: 3px solid var(--text-muted); margin-top: 1.5rem; font-size: 0.95rem;">
                <h4 style="color: #fff; margin-bottom: 0.5rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Context Analysis</h4>
                <p style="color: var(--text-muted); line-height: 1.6; margin-bottom: 1rem;">{analysis}</p>
                
                <h4 style="color: #fff; margin-bottom: 0.5rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Bias Breakdown</h4>
                <p style="color: var(--text-muted); line-height: 1.6;">{bias}</p>
            </div>
            
            <a href="{article['link']}" target="_blank" style="display: inline-block; margin-top: 1.5rem; color: #fff; text-decoration: none; font-size: 0.85rem; border: 1px solid rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 4px; transition: all 0.2s;">
                Verify Original Source ↗
            </a>
        </div>"""
                html_cards += card_html
                print(f"Success: {title}")
                break 
                
            except Exception as e:
                if "503" in str(e) or "429" in str(e):
                    print("Server busy. Waiting 5 seconds...")
                    time.sleep(5)
                else:
                    print(f"Data formatting error on attempt {attempt+1}: {e}")
                    if attempt == max_retries - 1:
                        print("Skipping article after 3 failed attempts.")
        
        time.sleep(4) 
            
    return html_cards

def update_html(new_content):
    if not new_content.strip():
        print("CRITICAL: No AI content generated. Pushing user reports only.")
        
    with open('index.html', 'r', encoding='utf-8') as file:
        html = file.read()
        
    pattern = r'(<section class="news-grid" id="news-container">)(.*?)(</section>)'
    # We push updates even if the AI content is empty, so your reports always show
    updated_html = re.sub(pattern, r'\1\n' + new_content + r'\n\3', html, flags=re.DOTALL)
    
    with open('index.html', 'w', encoding='utf-8') as file:
        file.write(updated_html)

if __name__ == "__main__":
    user_reports = get_user_reports()
    news_items = get_latest_news()
    ai_news = generate_neutral_content(news_items)
    final_content = user_reports + ai_news
    update_html(final_content)
    print("Deployment complete!")
