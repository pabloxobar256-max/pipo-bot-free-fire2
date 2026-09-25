#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 𝑷𝑰𝑷𝑶  𝑫𝑶𝑾𝑵𝑳𝑶𝑨𝑫 — نسخة نهائية مع cookies + proxy

import os
import re
import time
import shutil
import sqlite3
import threading
from datetime import datetime

import telebot
from telebot import types
from flask import Flask
import yt_dlp

# ==================== الإعدادات ====================
BOT_TOKEN = "8819449250:AAHkz6pfTyUTAGZgipCjQvl2VH4CreP7Wp0"
ADMIN_ID = 8050958688
SUPPORT_USER = "amirx_xpipo"
BOT_NAME = "𝑷𝑰𝑷𝑶  𝑫𝑶𝑾𝑵𝑳𝑶𝑨𝑫"
ADMIN_SECRET = "830714pipo"

# 🍪 ملف cookies
COOKIES_FILE = "cookies.txt"

# 🌐 Proxy (Webshare)
PROXY = "http://qjpttzgi:6i7gk0phvepr@p.webshare.io:80"

DOWNLOAD_DIR = "downloads"
DB_FILE = "pipo_bot.db"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== جلب صورة البوت ====================
BOT_PHOTO_ID = None

def load_bot_photo():
    global BOT_PHOTO_ID
    try:
        me = bot.get_me()
        photos = bot.get_user_profile_photos(me.id, limit=1)
        if photos.total_count > 0:
            BOT_PHOTO_ID = photos.photos[0][-1].file_id
            print("[+] Bot photo loaded")
        else:
            print("[!] لا توجد صورة للبوت")
    except Exception as e:
        print(f"[!] خطأ: {e}")

# ==================== FFmpeg ====================
_ff = shutil.which("ffmpeg")
if _ff:
    FFMPEG_PATH = _ff
    print(f"[+] FFmpeg: {FFMPEG_PATH}")
else:
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
        print("[+] FFmpeg (imageio)")
    except Exception:
        FFMPEG_PATH = "ffmpeg"
        print("[!] FFmpeg غير متوفر")

# ==================== Flask ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "PIPO Download Bot is running!"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT,
        banned INTEGER DEFAULT 0,
        downloads INTEGER DEFAULT 0,
        joined TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, url TEXT, platform TEXT, title TEXT,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, first_name TEXT,
        message TEXT,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

def db_query(q, p=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(q, p)
    r = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return r

# ==================== إدارة المستخدمين ====================
def add_user(uid, username, first_name):
    ex = db_query("SELECT user_id FROM users WHERE user_id=?", (uid,), True)
    if not ex:
        db_query("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                 (uid, username or "", first_name or ""))

def is_banned(uid):
    r = db_query("SELECT banned FROM users WHERE user_id=?", (uid,), True)
    return r and r[0][0] == 1

def inc_downloads(uid):
    db_query("UPDATE users SET downloads = downloads + 1 WHERE user_id=?", (uid,))

def log_history(uid, url, platform, title):
    db_query("INSERT INTO history (user_id, url, platform, title) VALUES (?, ?, ?, ?)",
             (uid, url, platform, title or ""))

def save_suggestion(uid, username, first_name, message):
    db_query("INSERT INTO suggestions (user_id, username, first_name, message) VALUES (?, ?, ?, ?)",
             (uid, username or "", first_name or "", message))

# ==================== كشف المنصة ====================
PLATFORMS = {
    'youtube.com': 'YouTube', 'youtu.be': 'YouTube',
    'instagram.com': 'Instagram', 'tiktok.com': 'TikTok',
    'twitter.com': 'Twitter/X', 'x.com': 'Twitter/X',
    'facebook.com': 'Facebook', 'fb.watch': 'Facebook',
    'snapchat.com': 'Snapchat', 'pinterest.com': 'Pinterest',
    'reddit.com': 'Reddit', 't.me': 'Telegram',
    'vimeo.com': 'Vimeo', 'dailymotion.com': 'Dailymotion',
    'twitch.tv': 'Twitch',
}

def detect_platform(url):
    for k, n in PLATFORMS.items():
        if k in url: return n
    return 'Unknown'

URL_REGEX = re.compile(r'https?://[^\s]+')

def extract_url(text):
    m = URL_REGEX.search(text) if text else None
    return m.group(0) if m else None

# ==================== التنزيل ====================
def download_ytdlp(url, user_id):
    """تنزيل بأفضل جودة مع cookies و proxy"""
    try:
        platform = detect_platform(url)
        safe_id = f"{user_id}_{int(time.time())}"
        out_tmpl = os.path.join(DOWNLOAD_DIR, f"{safe_id}.%(ext)s")

        fmt = 'bestvideo+bestaudio/best'

        ydl_opts = {
            'outtmpl': out_tmpl,
            'quiet': True,
            'no_warnings': True,
            'format': fmt,
            'merge_output_format': 'mp4',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'nocheckcertificate': True,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 60,
            'extractor_retries': 5,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }

        # 🍪 Cookies
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE
            print(f"[+] Using cookies: {COOKIES_FILE}")

        # 🌐 Proxy
        if PROXY:
            ydl_opts['proxy'] = PROXY
            print(f"[+] Using proxy")

        # إعدادات لكل منصة
        if 'youtube' in url or 'youtu.be' in url:
            ydl_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['web', 'android', 'ios'],
                }
            }
        elif 'tiktok' in url:
            ydl_opts['extractor_args'] = {
                'tiktok': {
                    'api_hostname': 'api22-normal-c-useast2a.tiktokv.com',
                }
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return None
            title = info.get('title', 'video')[:80]
            for ext in ['mp4', 'webm', 'mkv', 'm4a', 'mp3']:
                path = os.path.join(DOWNLOAD_DIR, f"{safe_id}.{ext}")
                if os.path.exists(path):
                    return {'path': path, 'title': title, 'platform': platform}
        return None
    except Exception as e:
        print(f"[ytdlp] ERROR: {e}")
        return None

def download_media(url, user_id):
    """كل المنصات عبر yt-dlp"""
    r = download_ytdlp(url, user_id)
    if r:
        ext = r['path'].split('.')[-1].lower()
        mtype = 'audio' if ext == 'mp3' else 'video'
        return {'type': mtype, 'path': r['path'], 'title': r.get('title', ''),
                'platform': r.get('platform', '')}
    return None

# ==================== لوحات المفاتيح ====================
def kb_services():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📥 تنزيل فيديو", callback_data="dl"),
        types.InlineKeyboardButton("📜 تاريخي", callback_data="s_history"),
    )
    kb.add(
        types.InlineKeyboardButton("📊 حالتي", callback_data="s_status"),
        types.InlineKeyboardButton("📋 المنصات", callback_data="s_platforms"),
    )
    kb.add(
        types.InlineKeyboardButton("ℹ️ كيف أستخدم", callback_data="s_help"),
        types.InlineKeyboardButton("💡 اقتراح ميزة", callback_data="suggest"),
    )
    kb.add(types.InlineKeyboardButton(f"🆘 الدعم @{SUPPORT_USER}",
                                       url=f"https://t.me/{SUPPORT_USER}"))
    return kb

def kb_back():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="s_back"))
    return kb

def kb_admin():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 إحصائيات", callback_data="a_stats"),
        types.InlineKeyboardButton("🏆 أفضل 10", callback_data="a_top"),
    )
    kb.add(
        types.InlineKeyboardButton("📢 إرسال جماعي", callback_data="a_broadcast"),
        types.InlineKeyboardButton("🚫 حظر", callback_data="a_ban"),
    )
    kb.add(
        types.InlineKeyboardButton("✅ رفع حظر", callback_data="a_unban"),
        types.InlineKeyboardButton("📥 آخر التنزيلات", callback_data="a_recent"),
    )
    kb.add(
        types.InlineKeyboardButton("📊 حسب المنصة", callback_data="a_platforms"),
        types.InlineKeyboardButton("🔍 بحث مستخدم", callback_data="a_search"),
    )
    kb.add(types.InlineKeyboardButton("💡 اقتراحات", callback_data="a_suggestions"))
    return kb

# ==================== /start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    add_user(uid, message.from_user.username, message.from_user.first_name)
    if is_banned(uid): return

    name = message.from_user.first_name or "صديقي"
    caption = (
        f"🔥 *أهلاً {name}*\n\n"
        f"📥 *{BOT_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ بوت تنزيلات مجاني\n"
        f"✅ يدعم 15+ منصة\n"
        f"🎬 جودة تلقائية مثالية\n"
        f"♾️ بلا حدود\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 أرسل رابطاً لتنزيله:"
    )

    if BOT_PHOTO_ID:
        try:
            bot.send_photo(message.chat.id, BOT_PHOTO_ID,
                           caption=caption,
                           reply_markup=kb_services(),
                           parse_mode='Markdown')
            return
        except:
            pass

    bot.send_message(message.chat.id, caption,
                     reply_markup=kb_services(),
                     parse_mode='Markdown',
                     disable_web_page_preview=True)

# ==================== الأزرار ====================
@bot.callback_query_handler(func=lambda c: True)
def cb_handler(call):
    uid = call.from_user.id
    data = call.data

    if data.startswith("a_") and uid == ADMIN_ID:
        handle_admin_cb(call, data)
        return

    if data == "s_back":
        name = call.from_user.first_name or "صديقي"
        caption = (
            f"🔥 *أهلاً {name}*\n\n"
            f"📥 *{BOT_NAME}*\n"
            f"👇 أرسل رابطاً:"
        )
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        if BOT_PHOTO_ID:
            try:
                bot.send_photo(call.message.chat.id, BOT_PHOTO_ID,
                               caption=caption,
                               reply_markup=kb_services(),
                               parse_mode='Markdown')
                bot.answer_callback_query(call.id, "🏠")
                return
            except:
                pass

        bot.send_message(call.message.chat.id, caption,
                         reply_markup=kb_services(),
                         parse_mode='Markdown')
        bot.answer_callback_query(call.id, "🏠")
        return

    if data == "suggest":
        bot.answer_callback_query(call.id, "💡")
        msg = bot.send_message(call.message.chat.id,
            "💡 *اقتراح ميزة*\n\n📝 أرسل اقتراحك:",
            parse_mode='Markdown')
        bot.register_next_step_handler(msg, do_suggestion, uid)
        return

    if data == "dl":
        bot.answer_callback_query(call.id, "📥")
        bot.send_message(call.message.chat.id, "📥 أرسل الرابط الآن.",
                         reply_markup=kb_back())
        return

    if data == "s_history":
        rows = db_query("SELECT url, platform, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10",
                        (uid,), True)
        if not rows:
            bot.answer_callback_query(call.id, "📜 فارغ")
            bot.send_message(call.message.chat.id, "📜 لا يوجد تاريخ.",
                             reply_markup=kb_back())
            return
        text = "📜 *آخر 10:*\n\n"
        for i, (url, plat, date) in enumerate(rows, 1):
            text += f"{i}. [{plat}] {date[:16]}\n"
        bot.answer_callback_query(call.id, "📜")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back(),
                         parse_mode='Markdown')
        return

    if data == "s_status":
        r = db_query("SELECT downloads, joined FROM users WHERE user_id=?", (uid,), True)
        dls = r[0][0] if r else 0
        joined = r[0][1] if r else ""
        text = f"📊 *حالتك*\n\n🆔 `{uid}`\n📥 تنزيلاتك: {dls}\n📅 {joined[:10]}"
        bot.answer_callback_query(call.id, "📊")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back(),
                         parse_mode='Markdown')
        return

    if data == "s_platforms":
        text = (
            "📋 *المنصات المدعومة:*\n\n"
            "• YouTube\n• TikTok\n• Instagram\n"
            "• Twitter / X\n• Facebook\n• Snapchat\n"
            "• Pinterest\n• Reddit\n• Telegram\n"
            "• Vimeo\n• Dailymotion\n• Twitch"
        )
        bot.answer_callback_query(call.id, "📋")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back(),
                         parse_mode='Markdown')
        return

    if data == "s_help":
        text = "ℹ️ *كيف أستخدم:*\n\n1️⃣ أرسل رابط الفيديو.\n2️⃣ انتظر التنزيل."
        bot.answer_callback_query(call.id, "ℹ️")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back(),
                         parse_mode='Markdown')
        return

# ==================== الاقتراح ====================
def do_suggestion(message, uid):
    if not message.text:
        bot.reply_to(message, "❌ أرسل نصاً.")
        return
    text = message.text.strip()
    if text.startswith('/'):
        bot.reply_to(message, "❌ تم الإلغاء.")
        return

    username = message.from_user.username or "لا يوجد"
    first_name = message.from_user.first_name or "مستخدم"

    save_suggestion(uid, username, first_name, text)

    try:
        bot.send_message(ADMIN_ID,
            f"💡 *اقتراح جديد*\n\n"
            f"👤 {first_name}\n"
            f"🆔 `{uid}`\n"
            f"📛 @{username}\n\n"
            f"📝 {text}",
            parse_mode='Markdown')
    except:
        pass

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="s_back"))
    bot.send_message(message.chat.id, "✅ تم إرسال اقتراحك!", reply_markup=kb)

# ==================== لوحة المطور ====================
def handle_admin_cb(call, data):
    kb_back_a = types.InlineKeyboardMarkup()
    kb_back_a.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="a_back"))

    if data == "a_back":
        try:
            bot.edit_message_text("👑 لوحة المطور",
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id,
                                  reply_markup=kb_admin())
        except:
            bot.send_message(call.message.chat.id, "👑 لوحة المطور", reply_markup=kb_admin())
        bot.answer_callback_query(call.id, "👑")
        return

    if data == "a_stats":
        users = db_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]
        dls = db_query("SELECT COUNT(*) FROM history", fetch=True)[0][0]
        b = db_query("SELECT COUNT(*) FROM users WHERE banned=1", fetch=True)[0][0]
        sug = db_query("SELECT COUNT(*) FROM suggestions", fetch=True)[0][0]
        bot.answer_callback_query(call.id, "📊")
        bot.send_message(call.message.chat.id,
            f"📊 *إحصائيات*\n\n👥 {users}\n🚫 {b}\n📥 {dls}\n💡 {sug}",
            reply_markup=kb_back_a, parse_mode='Markdown')

    elif data == "a_top":
        rows = db_query("SELECT first_name, downloads FROM users ORDER BY downloads DESC LIMIT 10", fetch=True)
        text = "🏆 *أفضل 10:*\n\n"
        for i, (n, d) in enumerate(rows, 1):
            text += f"{i}. {n} — 📥{d}\n"
        bot.answer_callback_query(call.id, "🏆")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back_a, parse_mode='Markdown')

    elif data == "a_broadcast":
        bot.answer_callback_query(call.id, "📢")
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل:")
        bot.register_next_step_handler(msg, do_broadcast)

    elif data == "a_ban":
        bot.answer_callback_query(call.id, "🚫")
        msg = bot.send_message(call.message.chat.id, "ID:")
        bot.register_next_step_handler(msg, do_ban)

    elif data == "a_unban":
        bot.answer_callback_query(call.id, "✅")
        msg = bot.send_message(call.message.chat.id, "ID:")
        bot.register_next_step_handler(msg, do_unban)

    elif data == "a_recent":
        rows = db_query("SELECT user_id, platform, date FROM history ORDER BY id DESC LIMIT 15", fetch=True)
        text = "📥 *آخر 15:*\n\n"
        for u, p, d in rows:
            text += f"• {u} | {p} | {d[:16]}\n"
        bot.answer_callback_query(call.id, "📥")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back_a, parse_mode='Markdown')

    elif data == "a_platforms":
        rows = db_query("SELECT platform, COUNT(*) FROM history GROUP BY platform ORDER BY COUNT(*) DESC", fetch=True)
        text = "📊 *حسب المنصة:*\n\n"
        for p, c in rows:
            text += f"• {p}: {c}\n"
        bot.answer_callback_query(call.id, "📊")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back_a, parse_mode='Markdown')

    elif data == "a_search":
        bot.answer_callback_query(call.id, "🔍")
        msg = bot.send_message(call.message.chat.id, "ID:")
        bot.register_next_step_handler(msg, do_search)

    elif data == "a_suggestions":
        rows = db_query("SELECT first_name, username, message, date FROM suggestions ORDER BY id DESC LIMIT 15", fetch=True)
        if not rows:
            bot.answer_callback_query(call.id, "💡 فارغ")
            bot.send_message(call.message.chat.id, "💡 لا اقتراحات.", reply_markup=kb_back_a)
            return
        text = "💡 *آخر 15 اقتراح:*\n\n"
        for i, (name, un, msg, date) in enumerate(rows, 1):
            text += f"{i}. *{name}* (@{un})\n   {msg[:80]}\n\n"
        bot.answer_callback_query(call.id, "💡")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back_a, parse_mode='Markdown')

def do_broadcast(msg):
    if msg.from_user.id != ADMIN_ID: return
    users = db_query("SELECT user_id FROM users WHERE banned=0", fetch=True)
    ok = fail = 0
    for (u,) in users:
        try:
            bot.send_message(u, msg.text); ok += 1; time.sleep(0.05)
        except: fail += 1
    bot.reply_to(msg, f"✅ {ok} | ❌ {fail}")

def do_ban(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        db_query("UPDATE users SET banned=1 WHERE user_id=?", (u,))
        bot.reply_to(msg, f"🚫 {u}")
    except: bot.reply_to(msg, "❌")

def do_unban(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        db_query("UPDATE users SET banned=0 WHERE user_id=?", (u,))
        bot.reply_to(msg, f"✅ {u}")
    except: bot.reply_to(msg, "❌")

def do_search(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        r = db_query("SELECT * FROM users WHERE user_id=?", (u,), True)
        if not r: bot.reply_to(msg, "❌"); return
        row = r[0]
        bot.reply_to(msg, f"👤 {row[2]}\n🆔 {row[0]}\n📥 {row[4]}\n🚫 {'نعم' if row[3] else 'لا'}")
    except: bot.reply_to(msg, "❌")

# ==================== الكود السري ====================
@bot.message_handler(func=lambda m: m.text == ADMIN_SECRET)
def secret_admin(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "👑 *لوحة المطور*",
                     reply_markup=kb_admin(), parse_mode='Markdown')

# ==================== استقبال الروابط ====================
@bot.message_handler(func=lambda m: m.text and URL_REGEX.search(m.text))
def handle_url(message):
    uid = message.from_user.id
    chat_id = message.chat.id
    add_user(uid, message.from_user.username, message.from_user.first_name)
    if is_banned(uid): return

    url = extract_url(message.text)
    if not url: return
    platform = detect_platform(url)

    wait = bot.send_message(chat_id, f"⏳ جارٍ التنزيل من {platform}...")

    result = download_media(url, uid)

    if not result:
        bot.edit_message_text(
            f"❌ فشل التنزيل من {platform}\n\nجرب رابطاً آخر.",
            chat_id=chat_id, message_id=wait.message_id)
        return

    title = result.get('title', '')[:100]
    caption = f"✅ تم التنزيل\n📌 {title}\n🌐 {platform}"

    try:
        if result['type'] == 'video':
            with open(result['path'], 'rb') as f:
                bot.send_video(chat_id, f, caption=caption, supports_streaming=True)
            os.remove(result['path'])
        elif result['type'] == 'audio':
            with open(result['path'], 'rb') as f:
                bot.send_audio(chat_id, f, caption=caption)
            os.remove(result['path'])
        elif result['type'] == 'photo':
            with open(result['path'], 'rb') as f:
                bot.send_photo(chat_id, f, caption=caption)
            os.remove(result['path'])

        bot.delete_message(chat_id, wait.message_id)
        inc_downloads(uid)
        log_history(uid, url, platform, title)
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {e}", chat_id=chat_id, message_id=wait.message_id)

# ==================== رسائل أخرى ====================
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video'])
def handle_other(message):
    if message.text and message.text.startswith('/'):
        return
    bot.reply_to(message, "📌 أرسل رابط فيديو للتنزيل.")

# ==================== التشغيل ====================
if __name__ == '__main__':
    load_bot_photo()
    threading.Thread(target=run_flask, daemon=True).start()
    print("=" * 60)
    print(f"  🔥 {BOT_NAME}")
    print("=" * 60)
    print(f"  🎬 FFmpeg: {FFMPEG_PATH}")
    print(f"  🍪 Cookies: {'✓' if os.path.exists(COOKIES_FILE) else '✗'}")
    print(f"  🌐 Proxy: {'✓' if PROXY else '✗'}")
    print(f"  🖼️  Photo: {'✓' if BOT_PHOTO_ID else '✗'}")
    print("=" * 60)
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
