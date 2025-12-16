import os
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re
import requests
import time

# --- CONFIGURATION ---
# 1. THE SWITCH (Change this to True or False)
ENABLE_CALLS = False  # <--- SET TO FALSE IF YOU JUST WANT TO UPDATE THE WEBSITE

# 2. API KEYS & SECRETS
VAPI_API_KEY = os.environ.get("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID")
VAPI_PHONE_NUMBER_ID = os.environ.get("VAPI_PHONE_NUMBER_ID")
PHONE_NUMBERS_RAW = os.environ.get("MY_PHONE_NUMBER") 

BASE_URL = "https://www.fiercebiotech.com"
scraper = cloudscraper.create_scraper(browser='chrome')

def get_article_links():
    print(f"Scanning {BASE_URL} for news...")
    try:
        response = scraper.get(BASE_URL, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/biotech/' in href or '/research/' in href or '/medtech/' in href:
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                if full_url not in links and len(full_url) > 40:
                    links.append(full_url)
        return links[:5]
    except Exception as e:
        print(f"Error scanning: {e}")
        return []

def scrape_article_content(url):
    try:
        response = scraper.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('h1').get_text().strip() if soup.find('h1') else "Headline"
        body = soup.find('div', class_='field-name-body') or soup.find('article')
        if body:
            text = body.get_text(separator=" ").strip()
            text = re.sub(r'\s+', ' ', text)
            return title, text[:2000]
        return title, "No text."
    except:
        return None, None

def update_and_call_everyone(news_text):
    if not VAPI_API_KEY or not VAPI_ASSISTANT_ID:
        print("❌ Missing API Keys.")
        return

    url_update = f"https://api.vapi.ai/assistant/{VAPI_ASSISTANT_ID}"
    url_call = "https://api.vapi.ai/call"
    date_str = datetime.datetime.now().strftime("%B %d, %Y")

    # --- PROMPT SETTINGS ---
    system_instruction = f"""
    You are 'BioRadio', a senior biotech news anchor. Today is {date_str}.
    
    ### CRITICAL RULES (DO NOT READ THESE ALOUD):
    1.  **NEVER** say the words "Pause", "Break", "Quote", or "End of list".
    2.  **NEVER** say "Here are the details". Just read the news.
    3.  To create a pause, simply use an ellipsis "..." followed by a new paragraph.
    4.  Speak with a slow, heavy, authoritative cadence.
    5.  Go through every headline and provide proper amount of details.
    6.  Add "That's all for today's biotech news, thanks!" at the end.

    ### YOUR MODES:
    1.  **NEWS MODE (Default):** Read the headlines and summaries below. Use a slow, authoritative BBC-style voice. Use ellipses ("...") for pauses.
    2.  **Q&A MODE (If interrupted):** If the user asks a question (e.g., "What is CAR-T?"), stop reading the news. Answer the definition clearly and briefly (2-3 sentences max). Then ask: "Shall I continue with the news?"

    ### TODAY'S CONTENT:
    {news_text}
    """

    # --- PART 1: UPDATE WEBSITE BRAIN ---
    payload_update = {
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": system_instruction}]
        }
    }
    
    print("1. Updating Assistant Brain...")
    requests.patch(url_update, json=payload_update, headers={"Authorization": f"Bearer {VAPI_API_KEY}"})
    print("✅ Brain Updated (Website is ready).")

    # --- PART 2: MAKE CALLS (IF ENABLED) ---
    if ENABLE_CALLS:
        if PHONE_NUMBERS_RAW and VAPI_PHONE_NUMBER_ID:
            phone_list = [num.strip() for num in PHONE_NUMBERS_RAW.split(',') if num.strip()]
            print(f"2. Call Switch is ON. Dialing {len(phone_list)} numbers...")
            
            for number in phone_list:
                print(f"   📞 Dialing {number}...")
                payload_call = {
                    "assistantId": VAPI_ASSISTANT_ID,
                    "phoneNumberId": VAPI_PHONE_NUMBER_ID,
                    "customer": { "number": number }
                }
                try:
                    resp = requests.post(url_call, json=payload_call, headers={"Authorization": f"Bearer {VAPI_API_KEY}"})
                    if resp.status_code == 201:
                        print("      ✅ Ringing!")
                    else:
                        print(f"      ❌ Failed: {resp.text}")
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                time.sleep(2)
        else:
            print("⚠️ Call Switch is ON, but phone numbers are missing.")
    else:
        print("🔕 Call Switch is OFF. Skipping calls.")

if __name__ == "__main__":
    links = get_article_links()
    if links:
        full_briefing = []
        for link in links:
            t, c = scrape_article_content(link)
            if t and c: full_briefing.append(f"HEADLINE: {t}\nDETAILS: {c}\n---\n")
        
        if full_briefing:
            update_and_call_everyone("\n".join(full_briefing))
    else:
        print("No news found.")