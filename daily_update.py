import os
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re
import requests

# --- CONFIGURATION ---
VAPI_API_KEY = os.environ.get("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID")
BASE_URL = "https://www.fiercebiotech.com"

# Initialize scraper
scraper = cloudscraper.create_scraper(browser='chrome')

def get_article_links():
    print(f"Scanning {BASE_URL} for news...")
    try:
        response = scraper.get(BASE_URL, timeout=15)
        if response.status_code != 200:
            print(f"❌ Blocked! Status Code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/biotech/' in href or '/research/' in href or '/medtech/' in href:
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                if full_url not in links and len(full_url) > 40:
                    links.append(full_url)
        
        print(f"✅ Found {len(links)} potential articles.")
        return links[:5]
    except Exception as e:
        print(f"Error scanning homepage: {e}")
        return []

def scrape_article_content(url):
    try:
        print(f"Scraping: {url}")
        response = scraper.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        title = soup.find('h1').get_text().strip() if soup.find('h1') else "Unknown Headline"
        
        article_body = soup.find('div', class_='field-name-body') or \
                       soup.find('div', class_='content__body') or \
                       soup.find('article')
        
        if article_body:
            text = article_body.get_text(separator=" ").strip()
            text = re.sub(r'\s+', ' ', text)
            return title, text[:2000]
            
        return title, "Content could not be extracted."
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return None, None

def update_vapi_agent(news_text):
    if not VAPI_API_KEY or not VAPI_ASSISTANT_ID:
        print("❌ Missing API Keys.")
        return

    url = f"https://api.vapi.ai/assistant/{VAPI_ASSISTANT_ID}"
    date_str = datetime.datetime.now().strftime("%B %d, %Y")

    system_instruction = f"""
    You are 'BioRadio', the daily biotech news anchor. Speak at a slow, deliberate pace.
    Today is {date_str}.
    
    ### INSTRUCTIONS:
    1. INTRO: Say "Good morning, here is your Fierce Biotech Daily Briefing."
    2. CONTENT: Summarize the stories below.
    3. INTERACTION: Answer technical questions using the DETAILS provided.
    
    ### TODAY'S NEWS:
    {news_text}
    """
    
    # --- THE FIX IS HERE ---
    # We must explicitly state the provider and model again
    payload = {
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction
                }
            ]
        }
    }
    
    resp = requests.patch(url, json=payload, headers={"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"})
    
    if resp.status_code == 200:
        print("✅ Vapi updated successfully!")
    else:
        print(f"❌ Vapi update failed: {resp.text}")

if __name__ == "__main__":
    links = get_article_links()
    if not links:
        print("No news found today.")
        exit()

    full_briefing = []
    for link in links:
        title, content = scrape_article_content(link)
        if title and content:
            full_briefing.append(f"HEADLINE: {title}\nDETAILS: {content}\n----------------\n")

    if full_briefing:
        update_vapi_agent("\n".join(full_briefing))