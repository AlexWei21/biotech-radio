import os
import requests
import feedparser
from bs4 import BeautifulSoup
import datetime

# --- CONFIGURATION ---
# We use Environment Variables for security (set these in GitHub later)
VAPI_API_KEY = os.environ.get("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID")
RSS_URL = "https://www.fiercebiotech.com/rss/fiercebiotech"

def scrape_article_text(url):
    """
    Visits the article link and extracts the main text.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # FierceBiotech: Main text is usually in 'field-name-body' or 'content__body'
        body = soup.find('div', class_='field-name-body')
        if not body:
            body = soup.find('div', class_='content__body')
        if not body:
            # Fallback: Try to find any article tag
            body = soup.find('article')

        if body:
            # Get text, strip extra whitespace
            text = body.get_text(separator=" ").strip()
            # Clean up: Remove generic footers if present
            text = text.replace("© 2025 Questex LLC", "")
            return " ".join(text.split())[:2000] # Limit to 2000 chars per article
            
        return "Content extraction failed. Please refer to the headline."
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return "Could not load article details."

def get_todays_news():
    """
    Parses RSS and formats the System Prompt.
    """
    print("Fetching RSS Feed...")
    feed = feedparser.parse(RSS_URL)
    
    news_content = []
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    # Process top 4 articles only (to keep context window manageable)
    for i, entry in enumerate(feed.entries[:4]):
        print(f"Processing ({i+1}/4): {entry.title}")
        details = scrape_article_text(entry.link)
        
        article_block = (
            f"STORY {i+1}: {entry.title}\n"
            f"DETAILS: {details}\n"
            "-----------------------------\n"
        )
        news_content.append(article_block)
        
    final_text = "\n".join(news_content)
    
    return current_date, final_text

def update_vapi(date_str, news_text):
    """
    Patches the Vapi Assistant with the new System Prompt.
    """
    url = f"https://api.vapi.ai/assistant/{VAPI_ASSISTANT_ID}"
    
    # This is the "Persona" prompt + The Dynamic News
    system_instruction = f"""
    You are 'BioRadio', an intelligent, professional biotech news anchor.
    Today's date is {date_str}.

    ### INSTRUCTIONS:
    1.  **Opening:** Start by welcoming the user to the 'Daily Biotech Briefing' and state today's date clearly.
    2.  **Headlines:** Read the headlines of the top stories first.
    3.  **Interaction:** If the user listens silently, pick the most important story and summarize the technical details (Mechanism of Action, Phase data, etc.).
    4.  **Q&A:** If the user interrupts with questions like "What was the p-value?" or "Who led the round?", look at the DETAILS section below to answer.
    5.  **Style:** Speak like a radio host (NPR/Bloomberg style). Do not read URLs. Do not say "Story 1" or "End of details".

    ### TODAY'S NEWS DATA:
    {news_text}
    """

    # Vapi API Payload Structure
    payload = {
        "model": {
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction
                }
            ]
        }
    }
    
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("Pushing update to Vapi...")
    response = requests.patch(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ Vapi Assistant Updated Successfully!")
    else:
        print(f"❌ Error updating Vapi: {response.status_code} - {response.text}")
        exit(1) # Fail the GitHub Action if Vapi update fails

if __name__ == "__main__":
    date, news = get_todays_news()
    if news:
        update_vapi(date, news)
    else:
        print("No news found today.")