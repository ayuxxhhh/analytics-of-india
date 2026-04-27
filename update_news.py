import glob
import json
import os
import sys
import time
import xml.etree.ElementTree as ET

import requests
from google import genai
from google.genai import types
from openai import OpenAI


def get_user_reports():
    reports = []
    if not os.path.exists("reports"):
        os.makedirs("reports")

    for file_path in glob.glob("reports/*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            lines = content.split("\n", 1)
            reports.append(
                {
                    "type": "report",
                    "title": lines[0].strip() if len(lines) > 0 else "Untitled Report",
                    "body": lines[1].strip() if len(lines) > 1 else "",
                }
            )
        except Exception as error:
            print(f"Error reading report: {error}")
    return reports


def get_latest_news():
    print("Fetching Times of India News...")
    # TOI is currently more reliable than Google News feeds from CI runners.
    url = "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        articles = [
            {"title": item.find("title").text, "link": item.find("link").text}
            for item in root.findall(".//item")[:10]
        ]
        return articles
    except Exception as error:
        print(f"RSS ERROR: {error}")
        return [{"error": f"RSS Fetch Failed: {error}"}]


def build_prompt(articles):
    articles_text = "\n".join([f"Title: {a['title']} | Link: {a['link']}" for a in articles])
    return f"""
Analyze these {len(articles)} news headlines. Return ONLY a valid JSON array.
Each object in the array MUST have these exact keys:
"title" (string), "summary" (string, 3 paragraphs separated by <br><br>), "analysis" (string), "bias" (string), "score" (integer 1-100), and "link" (string).
Articles:
{articles_text}
"""


def get_ai_provider():
    provider = os.environ.get("AI_PROVIDER", "gemini").strip().lower()
    if provider not in {"gemini", "openai"}:
        print(
            f"WARNING: AI_PROVIDER '{provider}' is not supported. Falling back to 'gemini'."
        )
        return "gemini"
    return provider


def generate_with_gemini(prompt):
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    client = genai.Client(api_key=gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return response.text


def generate_with_openai(prompt):
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=openai_api_key)
    response = client.responses.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        input=prompt,
        text={"format": {"type": "json_object"}},
    )

    output_text = response.output_text
    parsed = json.loads(output_text)

    # Normalize object-shaped JSON into array form to keep the output contract stable.
    if isinstance(parsed, dict) and "items" in parsed and isinstance(parsed["items"], list):
        return json.dumps(parsed["items"])
    if isinstance(parsed, dict) and "articles" in parsed and isinstance(
        parsed["articles"], list
    ):
        return json.dumps(parsed["articles"])
    if isinstance(parsed, list):
        return json.dumps(parsed)

    raise RuntimeError(
        "OpenAI response JSON was not an array. Expected list, or object with items/articles list."
    )


def generate_all_news(articles):
    if articles and "error" in articles[0]:
        return [
            {
                "type": "news",
                "title": "System Alert: Data Feed Blocked",
                "summary": articles[0]["error"],
                "analysis": "The news source blocked the server connection.",
                "bias": "N/A",
                "score": 100,
                "link": "#",
            }
        ]

    if not articles:
        return []

    prompt = build_prompt(articles)
    provider = get_ai_provider()
    max_retries = 4

    for attempt in range(max_retries):
        try:
            print(
                f"Asking AI to process data with provider '{provider}' "
                f"(Attempt {attempt + 1} of {max_retries})..."
            )

            if provider == "openai":
                output_text = generate_with_openai(prompt)
            else:
                output_text = generate_with_gemini(prompt)

            data = json.loads(output_text)
            for item in data:
                item["type"] = "news"
            return data
        except Exception as error:
            print(f"AI Error: {error}")
            if attempt < max_retries - 1:
                time.sleep(10)
            else:
                return [
                    {
                        "type": "news",
                        "title": "System Alert: AI Engine Timeout",
                        "summary": (
                            "The AI provider failed to process the request after "
                            f"{max_retries} attempts. Error: {str(error)}"
                        ),
                        "analysis": (
                            "This usually means the selected API is overloaded, "
                            "misconfigured, or rate-limited."
                        ),
                        "bias": "N/A",
                        "score": 100,
                        "link": "#",
                    }
                ]


if __name__ == "__main__":
    print("Gathering data...")
    user_reports = get_user_reports()
    articles = get_latest_news()
    ai_news = generate_all_news(articles)

    final_data = user_reports + ai_news

    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(final_data, file, ensure_ascii=False, indent=2)

    print(f"Successfully wrote {len(final_data)} items to data.json")
