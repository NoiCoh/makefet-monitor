import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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
        "disable_web_page_preview": False  # Keeps link previews clean
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
    
    # 1. Target all event and show links
    event_links = soup.find_all('a', href=re.compile(r'/event/|/show/'))
    
    current_events = {}
    for link in event_links:
        href = link.get('href', '')
        # Absolute URL formatting
        full_url = urljoin(BASE_URL, href)
        
        # Extract ID to use as a unique identifier key
        event_ids = re.findall(r'\d+', href)
        if event_ids:
            event_id = event_ids[0]
            title = link.get_text().strip() or "צפייה באירוע"
            
            # Save the text and the direct link
            current_events[event_id] = {
                "title": title,
                "url": full_url
            }

    # 2. Read previously saved event IDs
    old_event_ids = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_event_ids = set(line.strip() for line in f.readlines() if line.strip())

    # 3. Check strictly for NEW additions
    new_events_found = []
    if old_event_ids:  # Skip on the very first crawl baseline setup
        for event_id, data in current_events.items():
            if event_id not in old_event_ids:
                new_events_found.append(data)

    # 4. Construct message if new items exist
    if new_events_found:
        print(f"Found {len(new_events_found)} new events!")
        
        # Build markdown links: [Title text](URL)
        links_list = []
        for item in new_events_found:
            links_list.append(f"• [{item['title']}]({item['url']})")
        
        events_str = "\n".join(links_list)
        message = f"🔔 *Those are the new events uploaded:*\n\n{events_str}"
        send_telegram_message(message)
    else:
        print("No new events detected.")

    # 5. Save the state mapping
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        for eid in sorted(list(current_events.keys())):
            f.write(f"{eid}\n")

if __name__ == "__main__":
    main()
