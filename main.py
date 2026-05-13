import os
import time
import hashlib
import ssl
import urllib.request
import requests
import threading
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
CHAT_ID_2 = os.environ.get("CHAT_ID_2", "")
URL = "https://exidmet.dim.gov.az/dqq/ImtQeyd"
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))

BAKU_TZ = timezone(timedelta(hours=4))

state = {
    "last_hash": None,
    "last_check_time": None,
    "last_change_time": None,
    "last_change_data": None,
    "last_data": None,
    "started_at": None,
}

def baku_time():
    return datetime.now(BAKU_TZ).strftime("%d.%m.%Y %H:%M:%S")

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
        for row in rows[1:]:
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cols) >= 9:
                data.append({
                    "bos_yer": cols[6],
                    "unvan": cols[7],
                    "vezife_grupu": cols[8],
                    "tarix": cols[1],
                })

        content = table.get_text()
        page_hash = hashlib.md5(content.encode()).hexdigest()
        return page_hash, data, None

    except Exception as e:
        return None, None, str(e)

def format_rows(data):
    if not data:
        return "Məlumat yoxdur."
    lines = []
    for i, row in enumerate(data, 1):
        lines.append(
            f"<b>{i}.</b> 📍 {row['unvan'][:60]}\n"
            f"   👔 Vəzifə: <b>{row['vezife_grupu']}</b> | 🪑 Boş yer: <b>{row['bos_yer']}</b> | 📅 {row['tarix']}"
        )
    return "\n\n".join(lines)

def send_telegram(msg, chat_id=None):
    targets = [chat_id] if chat_id else [CHAT_ID, CHAT_ID_2]
    for chat in targets:
        if chat:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat, "text": msg, "parse_mode": "HTML"}
            )

# ── Komanda handler-ları ──────────────────────────────────────

def handle_start(chat_id):
    uptime = ""
    if state["started_at"]:
        delta = datetime.now(BAKU_TZ) - state["started_at"]
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes = rem // 60
        uptime = f"\n⏱ Uptime: <b>{hours}s {minutes}d</b>"
    send_telegram(
        f"✅ <b>DIM Monitor aktiv işləyir.</b>\n"
        f"🕐 Cari vaxt: {baku_time()}{uptime}\n"
        f"🔄 Yoxlama intervalı: <b>{CHECK_INTERVAL} saniyə</b>\n"
        f"🔗 {URL}",
        chat_id=chat_id
    )

def handle_check(chat_id):
    send_telegram("🔍 Səhifə yoxlanılır...", chat_id=chat_id)
    current_hash, data, error = get_table_data()
    if current_hash is None:
        send_telegram(f"⚠️ Xəta: {error}", chat_id=chat_id)
        return
    state["last_check_time"] = baku_time()
    state["last_data"] = data
    changed = ""
    if state["last_hash"] and current_hash != state["last_hash"]:
        changed = "\n\n🔔 <b>Dəyişiklik aşkarlandı!</b>"
        state["last_hash"] = current_hash
    send_telegram(
        f"📋 Cədvəldə <b>{len(data)} sətir</b> var.\n"
        f"🕐 Yoxlama vaxtı: {baku_time()}\n\n"
        + format_rows(data)
        + f"{changed}\n\n🔗 {URL}",
        chat_id=chat_id
    )

def handle_status(chat_id):
    last_check = state["last_check_time"] or "hələ yoxlanılmayıb"
    last_change = state["last_change_time"] or "hələ dəyişiklik olmayıb"
    row_count = len(state["last_data"]) if state["last_data"] else "?"
    hash_short = state["last_hash"][:12] + "..." if state["last_hash"] else "yoxdur"
    started = state["started_at"].strftime("%d.%m.%Y %H:%M:%S") if state["started_at"] else "?"
    send_telegram(
        f"📊 <b>Monitor Status</b>\n\n"
        f"🟢 Bot: <b>Aktiv</b>\n"
        f"🕐 Başlama: {started}\n"
        f"🔄 Son yoxlama: {last_check}\n"
        f"🔔 Son dəyişiklik: {last_change}\n"
        f"📋 Cədvəl sətirləri: <b>{row_count}</b>\n"
        f"#️⃣ Hash: <code>{hash_short}</code>\n"
        f"⏱ İnterval: <b>{CHECK_INTERVAL}s</b>",
        chat_id=chat_id
    )

def handle_last(chat_id):
    if not state["last_change_data"]:
        send_telegram("ℹ️ Hələ heç bir dəyişiklik qeydə alınmayıb.", chat_id=chat_id)
        return
    send_telegram(
        f"🔔 <b>Son dəyişiklik</b>\n"
        f"🕐 Vaxt: {state['last_change_time']}\n\n"
        + format_rows(state["last_change_data"])
        + f"\n\n🔗 {URL}",
        chat_id=chat_id
    )

# ── Telegram polling (komandaları dinləyir) ───────────────────

def poll_commands():
    offset = None
    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params=params,
                timeout=35
            )
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id", ""))
                if text.startswith("/start"):
                    handle_start(chat_id)
                elif text.startswith("/check"):
                    handle_check(chat_id)
                elif text.startswith("/status"):
                    handle_status(chat_id)
                elif text.startswith("/last"):
                    handle_last(chat_id)
        except Exception:
            time.sleep(5)

# ── Monitor loop ──────────────────────────────────────────────

def monitor_loop():
    last_hash = None
    check_count = 0
    daily_checks = 86400 // CHECK_INTERVAL

    while True:
        current_hash, data, error = get_table_data()
        state["last_check_time"] = baku_time()

        if current_hash is None:
            send_telegram(f"⚠️ Səhifəyə qoşulmaq mümkün olmadı:\n{error}")
        elif last_hash is None:
            last_hash = current_hash
            state["last_hash"] = current_hash
            state["last_data"] = data
            send_telegram(
                f"✅ İzləmə başladı. Cədvəldə <b>{len(data)} sətir</b> var.\n\n"
                + format_rows(data)
                + f"\n\n🔗 {URL}"
            )
        elif current_hash != last_hash:
            state["last_change_time"] = baku_time()
            state["last_change_data"] = data
            last_hash = current_hash
            state["last_hash"] = current_hash
            state["last_data"] = data
            send_telegram(
                f"🔔 <b>DIM səhifəsində dəyişiklik aşkarlandı!</b>\n"
                f"📋 Cədvəldə indi <b>{len(data)} sətir</b> var.\n\n"
                + format_rows(data)
                + f"\n\n🔗 {URL}"
            )
        else:
            state["last_data"] = data

        check_count += 1
        if check_count % daily_checks == 0:
            send_telegram(
                f"🟢 DIM Monitor aktiv işləyir.\n"
                f"🕐 {baku_time()}\n"
                f"📋 Cədvəldə hal-hazırda <b>{len(data) if data else '?'} sətir</b> var."
            )

        time.sleep(CHECK_INTERVAL)

# ── Main ──────────────────────────────────────────────────────

def main():
    state["started_at"] = datetime.now(BAKU_TZ)

    send_telegram(
        f"✅ DIM Monitor işə düşdü. Səhifə izlənilir...\n"
        f"🕐 Başlama vaxtı: {baku_time()}"
    )

    t = threading.Thread(target=poll_commands, daemon=True)
    t.start()

    monitor_loop()

if __name__ == "__main__":
    main()
