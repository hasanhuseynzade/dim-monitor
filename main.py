import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
URL = "https://exidmet.dim.gov.az/dqq/ImtQeyd"
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))

def get_page_hash():
    try:
        r = requests.get(URL, timeout=15, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        content = table.get_text() if table else r.text
        return hashlib.md5(content.encode()).hexdigest(), content
    except Exception as e:
        return None, str(e)

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    )

def main():
    send_telegram("✅ DIM Monitor işə düşdü. Səhifə izlənilir...")
    last_hash = None
    while True:
        current_hash, content = get_page_hash()
        if current_hash is None:
            send_telegram(f"⚠️ Səhifəyə qoşulmaq mümkün olmadı:\n{content}")
        elif last_hash is None:
            last_hash = current_hash
        elif current_hash != last_hash:
            send_telegram(
                f"🔔 <b>DIM səhifəsində dəyişiklik aşkarlandı!</b>\n"
                f"🔗 {URL}"
            )
            last_hash = current_hash
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
