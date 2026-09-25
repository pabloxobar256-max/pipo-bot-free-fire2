#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 𝑷𝑰𝑷𝑶  𝑫𝑶𝑾𝑵𝑳𝑶𝑨𝑫 — Instagram + TikTok + YouTube

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

COOKIES_FILE = "cookies.txt"

DOWNLOAD_DIR = "downloads"
DB_FILE = "pipo_bot.db"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== Flask (للـ Render) ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "PIPO Bot is running!"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==================== صورة البوت ====================
BOT_PHOTO_ID = None

def load_bot_photo():
    global BOT_PHOTO_ID
    try:
        me = bot.get_me()
        photos = bot.get_user_profile_photos(me.id, limit=1)
        if photos.total_count > 0:
            BOT_PHOTO_ID = photos.photos[0][-1].file_id
            print("[+] Bot photo loaded")
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

# ==================== إدارة ====================
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

# ==================== المنصات ====================
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

# ==================== Instagram (لا نلمسه — يعمل) ====================
def try_snapinsta(url):
    try:
        import requests
        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        api = 'https://snapinsta.app/api/ajaxSearch'
        r = requests.post(api, data={'q': url, 't': 'media', 'lang': 'en'}, headers=HEADERS, timeout=30)
        if r.status_code != 200: return None
        j = r.json()
        if 'data' not in j: return None
        html = j['data']
        videos = re.findall(r'href="(https://[^"]+\.mp4[^"]*)"', html)
        videos += re.findall(r'data-direct="(https://[^"]+)"', html)
        videos = list(dict.fromkeys(videos))
        if not videos:
            photos = re.findall(r'href="(https://[^"]+\.jpg[^"]*)"', html)
            if photos: return {'type': 'url_photo', 'url': photos[0]}
            return None
        return {'type': 'url_video', 'url': videos[0]}
    except Exception as e:
        print(f"[snapinsta] {e}")
        return None

def try_oembed(url):
    try:
        import requests
        from urllib.parse import quote
        r = requests.get(f'https://api.instagram.com/oembed/?url={quote(url)}',
                        headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200: return None
        j = r.json()
        if 'thumbnail_url' not in j: return None
        return {'type': 'url_photo', 'url': j['thumbnail_url']}
    except Exception as e:
        print(f"[oembed] {e}")
        return None

def download_instagram(url):
    """Instagram — لا نلمسه، يعمل"""
    for func in [try_snapinsta, try_oembed]:
        result = func(url)
        if result:
            print(f"[+] Instagram via {func.__name__}")
            return result
        time.sleep(0.5)
    return None

# ==================== TikTok + YouTube + الباقي عبر yt-dlp ====================
def download_ytdlp(url, user_id):
    """TikTok + YouTube + Facebook + Twitter + الباقي"""
    try:
        platform = detect_platform(url)
        safe_id = f"{user_id}_{int(time.time())}"
        out_tmpl = os.path.join(DOWNLOAD_DIR, f"{safe_id}.%(ext)s")

        ydl_opts = {
            'outtmpl': out_tmpl,
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'nocheckcertificate': True,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 60,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        # إعدادات TikTok
        if 'tiktok' in url:
            ydl_opts['extractor_args'] = {
                'tiktok': {
                    'api_hostname': 'api22-normal-c-useast2a.tiktokv.com',
                    'app_version': '34.0.5',
                    'manifest_app_version': '34.0.5',
                }
            }
        # إعدادات YouTube
        elif 'youtube' in url or 'youtu.be' in url:
            ydl_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['web', 'android', 'ios', 'tv_embedded'],
                }
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None: return None
            title = info.get('title', 'video')[:80]
            for ext in ['mp4', 'webm', 'mkv', 'm4a', 'mp3']:
                path = os.path.join(DOWNLOAD_DIR, f"{safe_id}.{ext}")
                if os.path.exists(path):
                    return {'type': 'file', 'path': path, 'title': title, 'platform': platform}
        return None
    except Exception as e:
        print(f"[ytdlp] ERROR: {e}")
        return None

def download_media(url, user_id):
    platform = detect_platform(url)
    if platform == 'Instagram':
        r = download_instagram(url)
        if r: return r
    r = download_ytdlp(url, user_id)
    if r: return r
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

    try:
        if BOT_PHOTO_ID:
            bot.send_photo(message.chat.id, BOT_PHOTO_ID,
                           caption=caption, reply_markup=kb_services(),
                           parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, caption,
                             reply_markup=kb_services(),
                             parse_mode='Markdown',
                             disable_web_page_preview=True)
    except Exception as e:
        print(f"[cmd_start] {e}")

# ==================== الأزرار ====================
@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    uid = call.from_user.id
    data = call.data

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    if data.startswith("a_") and uid == ADMIN_ID:
        handle_admin_cb(call, data)
        return

    if data == "s_back":
        name = call.from_user.first_name or "صديقي"
        caption = f"🔥 *أهلاً {name}*\n\n📥 *{BOT_NAME}*\n👇 أرسل رابطاً:"
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        try:
            if BOT_PHOTO_ID:
                bot.send_photo(call.message.chat.id, BOT_PHOTO_ID,
                               caption=caption, reply_markup=kb_services(),
                               parse_mode='Markdown')
            else:
                bot.send_message(call.message.chat.id, caption,
                                 reply_markup=kb_services(), parse_mode='Markdown')
        except:
            pass
        return

    if data == "suggest":
        try:
            msg = bot.send_message(call.message.chat.id,
                "💡 *اقتراح ميزة*\n\n📝 أرسل اقتراحك:", parse_mode='Markdown')
            bot.register_next_step_handler(msg, do_suggestion, uid)
        except:
            pass
        return

    if data == "dl":
        try:
            bot.send_message(call.message.chat.id, "📥 أرسل الرابط الآن.",
                             reply_markup=kb_back())
        except:
            pass
        return

    if data == "s_history":
        rows = db_query("SELECT url, platform, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10",
                        (uid,), True)
        if not rows:
            try:
                bot.send_message(call.message.chat.id, "📜 لا يوجد تاريخ.",
                                 reply_markup=kb_back())
            except:
                pass
            return
        text = "📜 *آخر 10:*\n\n"
        for i, (url, plat, date) in enumerate(rows, 1):
            text += f"{i}. [{plat}] {date[:16]}\n"
        try:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=kb_back(), parse_mode='Markdown')
        except:
            pass
        return

    if data == "s_status":
        r = db_query("SELECT downloads, joined FROM users WHERE user_id=?", (uid,), True)
        dls = r[0][0] if r else 0
        joined = r[0][1] if r else ""
        text = f"📊 *حالتك*\n\n🆔 `{uid}`\n📥 تنزيلاتك: {dls}\n📅 {joined[:10]}"
        try:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=kb_back(), parse_mode='Markdown')
        except:
            pass
        return

    if data == "s_platforms":
        text = ("📋 *المنصات المدعومة:*\n\n"
                "• YouTube\n• TikTok\n• Instagram\n"
                "• Twitter / X\n• Facebook\n• Snapchat\n"
                "• Pinterest\n• Reddit\n• Telegram\n"
                "• Vimeo\n• Dailymotion\n• Twitch")
        try:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=kb_back(), parse_mode='Markdown')
        except:
            pass
        return

    if data == "s_help":
        text = "ℹ️ *كيف أستخدم:*\n\n1️⃣ أرسل رابط الفيديو.\n2️⃣ انتظر التنزيل."
        try:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=kb_back(), parse_mode='Markdown')
        except:
            pass
        return

# ==================== الاقتراح ====================
def do_suggestion(message, uid):
    if not message.text: return
    text = message.text.strip()
    if text.startswith('/'): return
    username = message.from_user.username or "لا يوجد"
    first_name = message.from_user.first_name or "مستخدم"
    save_suggestion(uid, username, first_name, text)
    try:
        bot.send_message(ADMIN_ID,
            f"💡 *اقتراح جديد*\n\n👤 {first_name}\n🆔 `{uid}`\n"
            f"📛 @{username}\n\n📝 {text}",
            parse_mode='Markdown')
    except:
        pass
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="s_back"))
    try:
        bot.send_message(message.chat.id, "✅ تم إرسال اقتراحك!", reply_markup=kb)
    except:
        pass

# ==================== لوحة المطور ====================
def handle_admin_cb(call, data):
    kb_back_a = types.InlineKeyboardMarkup()
    kb_back_a.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="a_back"))

    def safe_send(text, markup=None):
        try:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=markup, parse_mode='Markdown')
        except:
            pass

    if data == "a_back":
        safe_send("👑 لوحة المطور", kb_admin())
        return

    if data == "a_stats":
        users = db_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]
        dls = db_query("SELECT COUNT(*) FROM history", fetch=True)[0][0]
        b = db_query("SELECT COUNT(*) FROM users WHERE banned=1", fetch=True)[0][0]
        sug = db_query("SELECT COUNT(*) FROM suggestions", fetch=True)[0][0]
        safe_send(f"📊 *إحصائيات*\n\n👥 {users}\n🚫 {b}\n📥 {dls}\n💡 {sug}", kb_back_a)

    elif data == "a_top":
        rows = db_query("SELECT first_name, downloads FROM users ORDER BY downloads DESC LIMIT 10", fetch=True)
        text = "🏆 *أفضل 10:*\n\n"
        for i, (n, d) in enumerate(rows, 1):
            text += f"{i}. {n} — 📥{d}\n"
        safe_send(text, kb_back_a)

    elif data == "a_broadcast":
        try:
            msg = bot.send_message(call.message.chat.id, "✍️ أرسل:")
            bot.register_next_step_handler(msg, do_broadcast)
        except:
            pass

    elif data == "a_ban":
        try:
            msg = bot.send_message(call.message.chat.id, "ID:")
            bot.register_next_step_handler(msg, do_ban)
        except:
            pass

    elif data == "a_unban":
        try:
            msg = bot.send_message(call.message.chat.id, "ID:")
            bot.register_next_step_handler(msg, do_unban)
        except:
            pass

    elif data == "a_recent":
        rows = db_query("SELECT user_id, platform, date FROM history ORDER BY id DESC LIMIT 15", fetch=True)
        text = "📥 *آخر 15:*\n\n"
        for u, p, d in rows:
            text += f"• {u} | {p} | {d[:16]}\n"
        safe_send(text, kb_back_a)

    elif data == "a_platforms":
        rows = db_query("SELECT platform, COUNT(*) FROM history GROUP BY platform ORDER BY COUNT(*) DESC", fetch=True)
        text = "📊 *حسب المنصة:*\n\n"
        for p, c in rows:
            text += f"• {p}: {c}\n"
        safe_send(text, kb_back_a)

    elif data == "a_search":
        try:
            msg = bot.send_message(call.message.chat.id, "ID:")
            bot.register_next_step_handler(msg, do_search)
        except:
            pass

    elif data == "a_suggestions":
        rows = db_query("SELECT first_name, username, message, date FROM suggestions ORDER BY id DESC LIMIT 15", fetch=True)
        if not rows:
            safe_send("💡 لا اقتراحات.", kb_back_a)
            return
        text = "💡 *آخر 15 اقتراح:*\n\n"
        for i, (name, un, msg, date) in enumerate(rows, 1):
            text += f"{i}. *{name}* (@{un})\n   {msg[:80]}\n\n"
        safe_send(text, kb_back_a)

def do_broadcast(msg):
    if msg.from_user.id != ADMIN_ID: return
    users = db_query("SELECT user_id FROM users WHERE banned=0", fetch=True)
    ok = fail = 0
    for (u,) in users:
        try:
            bot.send_message(u, msg.text); ok += 1; time.sleep(0.05)
        except: fail += 1
    try:
        bot.reply_to(msg, f"✅ {ok} | ❌ {fail}")
    except:
        pass

def do_ban(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        db_query("UPDATE users SET banned=1 WHERE user_id=?", (u,))
        bot.reply_to(msg, f"🚫 {u}")
    except:
        pass

def do_unban(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        db_query("UPDATE users SET banned=0 WHERE user_id=?", (u,))
        bot.reply_to(msg, f"✅ {u}")
    except:
        pass

def do_search(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        r = db_query("SELECT * FROM users WHERE user_id=?", (u,), True)
        if not r:
            bot.reply_to(msg, "❌")
            return
        row = r[0]
        bot.reply_to(msg, f"👤 {row[2]}\n🆔 {row[0]}\n📥 {row[4]}\n🚫 {'نعم' if row[3] else 'لا'}")
    except:
        pass

# ==================== الكود السري ====================
@bot.message_handler(func=lambda m: m.text == ADMIN_SECRET)
def secret_admin(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        bot.send_message(message.chat.id, "👑 *لوحة المطور*",
                         reply_markup=kb_admin(), parse_mode='Markdown')
    except:
        pass

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
        try:
            bot.edit_message_text(f"❌ فشل التنزيل من {platform}\n\nجرب رابطاً آخر.",
                                  chat_id=chat_id, message_id=wait.message_id)
        except:
            pass
        return

    title = result.get('title', '')[:100] if 'title' in result else ''
    caption = f"✅ تم التنزيل\n📌 {title}\n🌐 {platform}" if title else f"✅ تم التنزيل\n🌐 {platform}"

    try:
        if result['type'] == 'url_video':
            bot.send_video(chat_id, result['url'], caption=caption, supports_streaming=True)
        elif result['type'] == 'url_photo':
            bot.send_photo(chat_id, result['url'], caption=caption)
        elif result['type'] == 'file':
            ext = result['path'].split('.')[-1].lower()
            with open(result['path'], 'rb') as f:
                if ext == 'mp3':
                    bot.send_audio(chat_id, f, caption=caption)
                else:
                    bot.send_video(chat_id, f, caption=caption, supports_streaming=True)
            try: os.remove(result['path'])
            except: pass

        try:
            bot.delete_message(chat_id, wait.message_id)
        except:
            pass

        inc_downloads(uid)
        log_history(uid, url, platform, title)
    except Exception as e:
        print(f"[send] {e}")
        try:
            bot.edit_message_text(f"❌ خطأ: {e}",
                                  chat_id=chat_id, message_id=wait.message_id)
        except:
            pass

# ==================== رسائل أخرى ====================
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video'])
def handle_other(message):
    if message.text and message.text.startswith('/'):
        return
    try:
        bot.reply_to(message, "📌 أرسل رابط فيديو للتنزيل.")
    except:
        pass

# ==================== التشغيل ====================
if __name__ == '__main__':
    try:
        bot.remove_webhook()
        print("[+] Webhook cleared")
    except:
        pass

    load_bot_photo()
    threading.Thread(target=run_flask, daemon=True).start()

    print("=" * 60)
    print(f"  🔥 {BOT_NAME}")
    print("=" * 60)
    print(f"  🎬 FFmpeg: {FFMPEG_PATH}")
    print(f"  🍪 Cookies: {'✓' if os.path.exists(COOKIES_FILE) else '✗'}")
    print(f"  🖼️  Photo: {'✓' if BOT_PHOTO_ID else '✗'}")
    print("=" * 60)

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            print(f"[!] Polling error: {e}")
            time.sleep(5)
