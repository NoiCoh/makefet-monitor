import os
import hashlib
import requests
from bs4 import BeautifulSoup

# URL to monitor
URL = "https://makefet.smarticket.co.il/%D7%92%D7%99%D7%9C_%D7%94%D7%A8%D7%9A"
STATE_FILE = "last_state.txt"

# Retrieve tokens from environment variables (configured via GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """Sends a notification to your Telegram channel or chat."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration is missing.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Notification sent successfully.")
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
        print(f"Error fetching the page: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract the text content to detect structural changes.
    # Note: If the page has dynamic counters/clocks, you can narrow this down 
    # to a specific div element, e.g., soup.find('div', class_='events-list')
    page_text = soup.get_text()
    
    # Generate a hash of the content to quickly compare changes
    current_hash = hashlib.md5(page_text.encode('utf-8')).hexdigest()
    
    # Read the last known state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            old_hash = f.read().strip()
    else:
        old_hash = None

    # If the state exists and doesn't match the current hash, an event was added/changed
    if old_hash and current_hash != old_hash:
        print("Change detected! Sending notification...")
        message = f"🔔 *New event or change detected on the website!*\n\n🔗 [Click here to view the page]({URL})"
        send_telegram_message(message)
    else:
        print("No new changes detected.")

    # Save the current hash for the next run
    with open(STATE_FILE, "w") as f:
        f.write(current_hash)

if __name__ == "__main__":
    main()
