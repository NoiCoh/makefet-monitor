import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

BASE_URL = "https://makefet.smarticket.co.il/"
URL = "https://makefet.smarticket.co.il/%D7%92%D7%99%D7%9C_%D7%94%D7%A8%D7%9A"
STATE_FILE = "last_state.txt"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def clean_title(title_text):
    """Strips ugly whitespace, linebreaks, and irrelevant footer links."""
    if not title_text:
        return "אירוע חדש"
        
    # Replace multiple spaces/tabs/newlines with a single space
    clean = re.sub(r'\s+', ' ', title_text).strip()
    
    # Smarticket specific: If it grabbed dates or headers, extract the main name component
    # Try to grab text before common trailing links like 'גיל הרך' or 'דף הבית'
    for stop_word in ["גיל הרך", "דף הבית", "פרטים נוספים", "הכרטיסים אזלו"]:
        if stop_word in clean:
            clean = clean.split(stop_word)[0].strip()
            
    # Strip leading date stamps like '01יולי' or '10אוגוסט' if they stick to the title
    clean = re.sub(r'^\d+[א-ת]+\s*', '', clean)
    
    # Remove trailing commas/dashes
    clean = clean.rstrip(',- ').strip()
    
    return clean if len(clean) > 2 else "אירוע חדש"

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    event_links = soup.find_all('a', href=True)
    
    current_events = {}
    for link in event_links:
        href = link.get('href', '')
        full_url = urljoin(BASE_URL, href)
        
        parsed_url = urlparse(full_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'id' in query_params:
            event_id = query_params['id'][0]
            
            # If the link has an inner heading (like h2, h3, h4, or strong), use that instead of full text
            heading = link.find(['h2', 'h3', 'h4', 'strong', 'span'])
            raw_title = heading.get_text() if heading else link.get_text()
            
            title = clean_title(raw_title)
            
            current_events[event_id] = {
                "title": title,
                "url": full_url
            }

    old_event_ids = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_event_ids = set(line.strip() for line in f.readlines() if line.strip())

    new_events_found = []
    if old_event_ids:  
        for event_id, data in current_events.items():
            if event_id not in old_event_ids:
                new_events_found.append(data)

    # 4. Perfectly formatted minimalist layout
    if new_events_found:
        print(f"Found {len(new_events_found)} new events!")
        
        links_list = []
        for index, item in enumerate(new_events_found, 1):
            # Builds exactly the style you asked for:
            # 1. Title
            # - קישור -
            links_list.append(f"{index}. {item['title']}\n- [קישור]({item['url']}) -")
        
        events_str = "\n".join(links_list)
        message = f"Hi, you got new events 🙂:\n\n{events_str}"
        
        send_telegram_message(message)
    else:
        print(f"No new events. Total active tracked events on page: {len(current_events)}")

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        for eid in sorted(list(current_events.keys())):
            f.write(f"{eid}\n")

if __name__ == "__main__":
    main()
