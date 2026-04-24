import os
import re
import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai

# Configure the AI
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

def get_latest_news():
    # Fetch top news from India via RSS
    url = "https://news.google.com/rss?gl=IN&ceid=IN:en"
    response = requests.get(url)
    root = ET.fromstring(response.content)
    
    articles = []
    # Grab the top 6 articles
    for item in root.findall('.//item')[:6]:
        title = item.find('title').text
        articles.append(title)
    return articles

def generate_neutral_content(articles):
    html_cards = ""
    
    for article in articles:
        # Prompt the AI to rewrite the news in a clean, professional, unbiased way
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
            
            # Parse the AI response
            lines = text.split('\n')
            title = lines[0].replace('Title: ', '').strip()
            summary = lines[1].replace('Summary: ', '').strip()
            
            # Format into your website's HTML design
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
    # Open your existing website code
    with open('index.html', 'r', encoding='utf-8') as file:
        html = file.read()
        
    # Find the news grid section and replace everything inside it
    pattern = r'(<section class="news-grid" id="news-container">)(.*?)(</section>)'
    updated_html = re.sub(pattern, r'\1\n' + new_content + r'\n\3', html, flags=re.DOTALL)
    
    # Save the updated code
    with open('index.html', 'w', encoding='utf-8') as file:
        file.write(updated_html)

if __name__ == "__main__":
    print("Fetching news...")
    news_items = get_latest_news()
    print("Generating unbiased summaries via AI...")
    new_html_content = generate_neutral_content(news_items)
    print("Updating website...")
    update_html(new_html_content)
    print("Done!")
