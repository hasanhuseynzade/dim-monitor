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

def get_table_data():
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
        if not table:
            return None, None, "Cədvəl tapılmadı"

        rows = table.find_all("tr")
        data = []
        for row in rows[1:]:  # başlığı keç
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cols) >= 9:
                data.append({
                    "bos_yer": cols[6],       # Boş yerlərin sayı
                    "unvan": cols[7],          # Ünvan
                    "vezife_grupu": cols[8],   # Vəzifə qrupları
                    "tarix": cols[1],          # İmtahan tarixi
                })

        content = table.get_text()
        page_hash = hashlib.md5(content.encode()).hexdigest()
        return page_hash, data, None

    except Exception as e:
        return None, None, str(e)

def format_rows(data):
    lines = []
    for i, row in enumerate(data, 1):
        lines.append(
            f"<b>{i}.</b> 📍 {row['unvan'][:60]}\n"
            f"   👔 Vəzifə: <b>{row['vezife_grupu']}</b> | 🪑 Boş yer: <b>{row['bos_yer']}</b> | 📅 {row['tarix']}"
        )
    return "\n\n".join(lines)

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    )

def main():
    send_telegram("✅ DIM Monitor işə düşdü. Səhifə izlənilir...")
    last_hash = None

    while True:
        current_hash, data, error = get_table_data()

        if current_hash is None:
            send_telegram(f"⚠️ Səhifəyə qoşulmaq mümkün olmadı:\n{error}")
        elif last_hash is None:
            last_hash = current_hash
            msg = (
                f"✅ İzləmə başladı. Cədvəldə <b>{len(data)} sətir</b> var.\n\n"
                + format_rows(data)
            )
            send_telegram(msg)
        elif current_hash != last_hash:
            msg = (
                f"🔔 <b>DIM səhifəsində dəyişiklik aşkarlandı!</b>\n"
                f"📋 Cədvəldə indi <b>{len(data)} sətir</b> var.\n\n"
                + format_rows(data)
                + f"\n\n🔗 {URL}"
            )
            send_telegram(msg)
            last_hash = current_hash

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
