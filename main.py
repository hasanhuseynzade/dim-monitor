import os
import time
import hashlib
import ssl
import urllib.request
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
URL = "https://exidmet.dim.gov.az/dqq/ImtQeyd"
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))

def get_page_hash():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "az,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        req = urllib.request.Request(URL, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        content = table.get_text() if table else html
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
            send_telegram("✅ Səhifə uğurla oxundu. İzləmə başladı.")
        elif current_hash != last_hash:
            send_telegram(
                f"🔔 <b>DIM səhifəsində dəyişiklik aşkarlandı!</b>\n"
                f"🔗 {URL}"
            )
            last_hash = current_hash
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
