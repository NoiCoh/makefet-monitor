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
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

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
        
        # Parse out the URL query to look for the 'id' parameter (e.g., ?id=4317)
        parsed_url = urlparse(full_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'id' in query_params:
            event_id = query_params['id'][0] # This gets '4317'
            
            # Use link text or a clean default title
            title = link.get_text().strip()
            if not title or len(title) < 3: 
                title = "לחץ לצפייה באירוע" # Fallback Hebrew text ("Click to view event")
            
            # Map by event_id to prevent duplicates if the same link appears twice on the page
            current_events[event_id] = {
                "title": title,
                "url": full_url
            }

    # 2. Read previously saved event IDs
    old_event_ids = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_event_ids = set(line.strip() for line in f.readlines() if line.strip())

    # 3. Check for NEW events (Skip on first tracking run so you don't get flooded)
    new_events_found = []
    if old_event_ids:  
        for event_id, data in current_events.items():
            if event_id not in old_event_ids:
                new_events_found.append(data)

    # 4. Notify if new event(s) popped up
    if new_events_found:
        print(f"Found {len(new_events_found)} new events!")
        links_list = [f"• [{item['title']}]({item['url']})" for item in new_events_found]
        events_str = "\n".join(links_list)
        message = f"🔔 *Those are the new events uploaded:*\n\n{events_str}"
        send_telegram_message(message)
    else:
        print(f"No new events. Total active tracked events on page: {len(current_events)}")

    # 5. Save current IDs list to state file
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        for eid in sorted(list(current_events.keys())):
            f.write(f"{eid}\n")

if __name__ == "__main__":
    main()
