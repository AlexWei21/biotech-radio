import os
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re
import requests
import time

# --- CONFIGURATION ---
VAPI_API_KEY = os.environ.get("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID")
VAPI_PHONE_NUMBER_ID = os.environ.get("VAPI_PHONE_NUMBER_ID")
PHONE_NUMBERS_RAW = os.environ.get("MY_PHONE_NUMBER") # Comma separated list

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

    # --- THE "SLOW MODE" PROMPT ---
    system_instruction = f"""
    You are 'BioRadio', a senior biotech news anchor. Today is {date_str}.
    
    ### VOICE & STYLE GUIDELINES (CRITICAL):
    1.  **PACING:** Speak SLOWLY. I repeat, speak SLOWLY.
    2.  **PAUSING:** You MUST pause for 2 full seconds between headlines.
    3.  **TONE:** Use a deep, serious, and authoritative tone (BBC News style).
    4.  **NO FILLERS:** Do not say "Got it" or "Sure". Just read the news.
    
    ### INSTRUCTIONS:
    1.  Start immediately with: "Good morning. This is your Fierce Biotech Daily Briefing."
    2.  Read the headlines and details below using the pacing guidelines above.
    3.  If the call goes to voicemail or silence, HANG UP immediately.

    ### TODAY'S NEWS:
    {news_text}
    """

    # 2. UPDATE THE BRAIN
    payload_update = {
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "system", "content": system_instruction}]
        }
    }
    
    print("1. Updating Assistant Brain (Setting: Slow & Professional)...")
    requests.patch(url_update, json=payload_update, headers={"Authorization": f"Bearer {VAPI_API_KEY}"})
    print("✅ Brain Updated.")

    # 3. CALL EVERYONE
    if PHONE_NUMBERS_RAW and VAPI_PHONE_NUMBER_ID:
        phone_list = [num.strip() for num in PHONE_NUMBERS_RAW.split(',') if num.strip()]
        
        print(f"2. Dialing {len(phone_list)} numbers...")
        
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
        print("⚠️ Skipping calls (Missing Numbers or ID)")
        
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