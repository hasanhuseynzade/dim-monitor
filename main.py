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

def get_page_data():
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
        if table:
            rows = table.find_all("tr")
            row_count = len(rows) - 1  # başlıq sətri çıxılır
            content = table.get_text()
        else:
            row_count = 0
            content = html
        page_hash = hashlib.md5(content.encode()).hexdigest()
        return page_hash, row_count
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
    last_row_count = None

    while True:
        current_hash, row_count = get_page_data()

        if current_hash is None:
            send_telegram(f"⚠️ Səhifəyə qoşulmaq mümkün olmadı:\n{row_count}")
        elif last_hash is None:
            last_hash = current_hash
            last_row_count = row_count
            send_telegram(f"✅ Səhifə uğurla oxundu. İzləmə başladı.\n📋 Cədvəldə hal-hazırda <b>{row_count} sətir</b> var.")
        elif current_hash != last_hash:
            if row_count != last_row_count:
                diff = row_count - last_row_count
                arrow = "🟢 +" if diff > 0 else "🔴"
                change_info = f"{arrow}{diff} sətir ({last_row_count} → {row_count})"
            else:
                change_info = "Sətir sayı eynidir, amma məlumat dəyişib"

            send_telegram(
                f"🔔 <b>DIM səhifəsində dəyişiklik aşkarlandı!</b>\n"
                f"📋 {change_info}\n"
                f"🔗 {URL}"
            )
            last_hash = current_hash
            last_row_count = row_count

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
