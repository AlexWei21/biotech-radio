import os
import requests
from bs4 import BeautifulSoup
import datetime
import re

# --- CONFIGURATION ---
VAPI_API_KEY = os.environ.get("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID")
BASE_URL = "https://www.fiercebiotech.com"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_article_links():
    """
    Scrapes the homepage for the latest article URLs.
    """
    print(f"Scanning {BASE_URL} for news...")
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        # Strategy: Find all links that look like news articles
        # FierceBiotech usually puts articles in /biotech/ or /research/ paths
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Filter for valid article paths (exclude jobs, events, generic pages)
            if '/biotech/' in href or '/research/' in href or '/medtech/' in href:
                # Ensure full URL
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                
                # Avoid duplicates and non-article pages (like category pages)
                if full_url not in links and len(full_url) > 40:
                    links.append(full_url)
        
        # Return top 5 unique links (homepage usually orders by latest)
        return links[:5]
    except Exception as e:
        print(f"Error scanning homepage: {e}")
        return []

def scrape_article_content(url):
    """
    Visits a specific article URL and extracts the body text.
    """
    try:
        print(f"Scraping: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Get Title
        title_tag = soup.find('h1')
        title = title_tag.get_text().strip() if title_tag else "Unknown Headline"

        # 2. Get Body
        # FierceBiotech uses various classes; we try the most common ones.
        article_body = soup.find('div', class_='field-name-body') or \
                       soup.find('div', class_='content__body') or \
                       soup.find('article')
        
        if article_body:
            # Get text and clean it
            text = article_body.get_text(separator=" ").strip()
            # Remove "junk" text often found in footers/sidebars
            text = re.sub(r'\s+', ' ', text) # Collapse multiple spaces
            return title, text[:2500] # Limit to 2500 chars
            
        return title, "Content could not be extracted."
        
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return None, None

def update_vapi_agent(news_text):
    url = f"https://api.vapi.ai/assistant/{VAPI_ASSISTANT_ID}"
    date_str = datetime.datetime.now().strftime("%B %d, %Y")

    system_instruction = f"""
    You are 'BioRadio', the daily biotech news anchor.
    Today is {date_str}.
    
    ### INSTRUCTIONS:
    1. INTRO: Say "Good morning, here is your Fierce Biotech Daily Briefing."
    2. CONTENT: Use the provided news below. Summarize the top stories.
    3. STYLE: Professional, fast-paced, insightful.
    4. INTERACTIVE: If the user asks a technical question (e.g. "What's the p-value?"), answer it using the details provided.
    
    ### TODAY'S NEWS:
    {news_text}
    """

    payload = { "model": { "messages": [ { "role": "system", "content": system_instruction } ] } }
    
    # Check if keys are present (for local testing)
    if not VAPI_API_KEY or not VAPI_ASSISTANT_ID:
        print("❌ Missing API Keys. Export VAPI_API_KEY and VAPI_ASSISTANT_ID.")
        return

    resp = requests.patch(url, json=payload, headers={"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"})
    
    if resp.status_code == 200:
        print("✅ Vapi updated successfully.")
    else:
        print(f"❌ Vapi update failed: {resp.text}")

if __name__ == "__main__":
    links = get_article_links()
    
    if not links:
        print("No links found on homepage.")
        exit()

    full_briefing = []
    
    for link in links:
        title, content = scrape_article_content(link)
        if title and content:
            full_briefing.append(f"HEADLINE: {title}\nDETAILS: {content}\n----------------\n")

    if full_briefing:
        final_text = "\n".join(full_briefing)
        update_vapi_agent(final_text)
    else:
        print("No articles successfully scraped.")