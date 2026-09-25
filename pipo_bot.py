#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# insta_bot.py — بوت تنزيل فيديوهات إنستغرام بدون علامة مائية
# التشغيل: python insta_bot.py

import os
import re
import time
import requests
import telebot
from telebot import types
from urllib.parse import quote

# ==================== الإعدادات ====================
BOT_TOKEN = "8819449250:AAHkz6pfTyUTAGZgipCjQvl2VH4CreP7Wp0"
ADMIN_ID = 8050958688

# ==================== إعداد البوت ====================
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== رؤوس الطلبات ====================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'X-Requested-With': 'XMLHttpRequest',
}

# ==================== Regex لرابط إنستغرام ====================
INSTA_REGEX = re.compile(
    r'(https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+)'
)

def extract_url(text):
    if not text:
        return None
    match = INSTA_REGEX.search(text)
    if match:
        return match.group(1)
    return None

# ==================== snapinsta ====================
def try_snapinsta(url):
    try:
        api = 'https://snapinsta.app/api/ajaxSearch'
        data = {'q': url, 't': 'media', 'lang': 'en'}
        r = requests.post(api, data=data, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        j = r.json()
        if 'data' not in j:
            return None
        html = j['data']
        videos = re.findall(r'href="(https://[^"]+\.mp4[^"]*)"', html)
        videos += re.findall(r'data-direct="(https://[^"]+)"', html)
        videos = list(dict.fromkeys(videos))
        if not videos:
            photos = re.findall(r'href="(https://[^"]+\.jpg[^"]*)"', html)
            if photos:
                return {'type': 'photo', 'url': photos[0], 'thumbnail': photos[0]}
            return None
        thumb = None
        tm = re.search(r'<img src="(https://[^"]+\.jpg[^"]*)"', html)
        if tm:
            thumb = tm.group(1)
        return {'type': 'video', 'url': videos[0], 'thumbnail': thumb}
    except Exception as e:
        print(f"[snapinsta] {e}")
        return None

# ==================== savefrom ====================
def try_savefrom(url):
    try:
        api = 'https://api.savefrom.net/api/convert'
        data = {'url': url}
        r = requests.post(api, data=data, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        j = r.json()
        if 'url' not in j:
            return None
        return {'type': 'video', 'url': j['url'], 'thumbnail': j.get('thumb')}
    except Exception as e:
        print(f"[savefrom] {e}")
        return None

# ==================== oembed ====================
def try_oembed(url):
    try:
        api = f'https://api.instagram.com/oembed/?url={quote(url)}'
        r = requests.get(api, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        j = r.json()
        if 'thumbnail_url' not in j:
            return None
        return {'type': 'photo', 'url': j['thumbnail_url'], 'thumbnail': j['thumbnail_url']}
    except Exception as e:
        print(f"[oembed] {e}")
        return None

# ==================== ssyoutube ====================
def try_ssyoutube(url):
    try:
        api = 'https://ssyoutube.com/api/convert'
        data = {'url': url}
        r = requests.post(api, data=data, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        j = r.json()
        if 'url' not in j:
            return None
        return {'type': 'video', 'url': j['url'], 'thumbnail': j.get('thumb')}
    except Exception as e:
        print(f"[ssyoutube] {e}")
        return None

# ==================== الدالة الرئيسية ====================
def download_instagram(url):
    for func in [try_snapinsta, try_savefrom, try_oembed, try_ssyoutube]:
        result = func(url)
        if result:
            print(f"[+] نجح: {func.__name__}")
            return result
        time.sleep(0.5)
    return None

# ==================== لوحة المفاتيح ====================
def main_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("💰 شراء نسخة", url="https://t.me/iiiiZBot"),
        types.InlineKeyboardButton("☎️ المطور", url="https://t.me/iiiiZ"),
    )
    return kb

# ==================== /start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "مستخدم"

    text = (
        "📥 بوت تنزيل فيديوهات إنستغرام\n\n"
        f"👋 مرحباً {name}\n\n"
        "📌 أرسل رابط أي فيديو من إنستغرام، وسأرسله لك بدون علامة مائية.\n\n"
        "⚡ يدعم: Reels, Posts, IGTV\n"
        "🔞 لا يدعم: Story, Highlights"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard(),
        disable_web_page_preview=True
    )

# ==================== /stats ====================
@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open('users.txt', 'r') as f:
            users = [l.strip() for l in f.readlines() if l.strip()]
        bot.reply_to(message, f"📊 إحصائيات البوت\n\n👥 المستخدمين: {len(users)}")
    except FileNotFoundError:
        bot.reply_to(message, "📊 لا يوجد مستخدمين بعد.")

# ==================== /broadcast ====================
@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "✍️ أرسل الرسالة الآن:")
    bot.register_next_step_handler(msg, do_broadcast)

def do_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open('users.txt', 'r') as f:
            users = [l.strip() for l in f.readlines() if l.strip()]
    except FileNotFoundError:
        bot.reply_to(message, "❌ لا يوجد مستخدمين.")
        return

    success = 0
    fail = 0
    for uid in users:
        try:
            bot.send_message(int(uid), message.text)
            success += 1
            time.sleep(0.05)
        except Exception:
            fail += 1

    bot.reply_to(message, f"✅ تم الإرسال\n✔️ نجح: {success}\n❌ فشل: {fail}")

# ==================== تسجيل المستخدمين ====================
def save_user(user_id):
    try:
        users = []
        if os.path.exists('users.txt'):
            with open('users.txt', 'r') as f:
                users = [l.strip() for l in f.readlines()]
        if str(user_id) not in users:
            with open('users.txt', 'a') as f:
                f.write(f"{user_id}\n")
    except Exception as e:
        print(f"[save_user] {e}")

# ==================== معالجة روابط إنستغرام ====================
@bot.message_handler(func=lambda m: m.text and 'instagram.com' in m.text)
def handle_instagram(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    name = message.from_user.first_name or "مستخدم"

    save_user(user_id)

    url = extract_url(message.text)
    if not url:
        bot.reply_to(message, "❌ الرابط غير صالح.")
        return

    wait_msg = bot.reply_to(message, f"⏳ جارٍ التنزيل...\n\n🔗 {url}")

    result = download_instagram(url)

    if not result:
        bot.edit_message_text(
            "❌ فشل التنزيل\n\n"
            "الأسباب المحتملة:\n"
            "• الحساب خاص\n"
            "• الفيديو محذوف\n"
            "• خطأ مؤقت في السيرفر\n\n"
            "جرب لاحقاً أو استخدم رابط آخر.",
            chat_id=chat_id,
            message_id=wait_msg.message_id
        )
        return

    caption = "✅ تم التنزيل بنجاح!\n\n📌 بدون علامة مائية"

    try:
        if result['type'] == 'video':
            bot.send_video(
                chat_id,
                result['url'],
                caption=caption,
                reply_markup=main_keyboard(),
                supports_streaming=True
            )
        else:
            bot.send_photo(
                chat_id,
                result['url'],
                caption=caption,
                reply_markup=main_keyboard()
            )

        bot.delete_message(chat_id, wait_msg.message_id)

        try:
            bot.send_message(
                ADMIN_ID,
                f"📥 تنزيل جديد\n\n"
                f"👤 {name}\n"
                f"🆔 {user_id}\n"
                f"🔗 {url}"
            )
        except:
            pass

    except Exception as e:
        bot.edit_message_text(
            f"❌ خطأ في إرسال الملف\n\n{e}",
            chat_id=chat_id,
            message_id=wait_msg.message_id
        )

# ==================== رسائل عادية ====================
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def handle_other(message):
    bot.reply_to(message, "❓ لم أفهم رسالتك.\n\n📌 أرسل رابط إنستغرام للتنزيل.")

# ==================== التشغيل ====================
if __name__ == '__main__':
    print("=" * 50)
    print("  📥 Instagram Downloader Bot")
    print("=" * 50)
    print(f"  🤖 Token: {BOT_TOKEN[:20]}...")
    print(f"  👑 Admin: {ADMIN_ID}")
    print("=" * 50)
    print("  ✅ البوت يعمل")
    print("  ⏹️  Ctrl+C للإيقاف")
    print("=" * 50)

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except Exception as e:
            print(f"[!] خطأ: {e}")
            print("[!] إعادة المحاولة بعد 5 ثوانٍ...")
            time.sleep(5)
