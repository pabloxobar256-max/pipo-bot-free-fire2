#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 𝑷𝑰𝑷𝑶  𝑫𝑶𝑾𝑵𝑳𝑶𝑨𝑫 — نسخة PTB نهائية

import os
import re
import time
import shutil
import sqlite3
import threading
import logging
from datetime import datetime

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== Flask (للـ Render) ====================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "PIPO Bot is running!"

@flask_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

# ==================== FFmpeg ====================
_ff = shutil.which("ffmpeg")
if _ff:
    FFMPEG_PATH = _ff
    print(f"[+] FFmpeg: {FFMPEG_PATH}")
else:
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    except:
        FFMPEG_PATH = "ffmpeg"

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
        message TEXT, date TEXT DEFAULT CURRENT_TIMESTAMP
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

# ==================== Instagram ====================
def try_snapinsta(url):
    try:
        import requests
        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        r = requests.post('https://snapinsta.app/api/ajaxSearch',
                          data={'q': url, 't': 'media', 'lang': 'en'},
                          headers=HEADERS, timeout=30)
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
    except:
        return None

def download_instagram(url):
    for func in [try_snapinsta, try_oembed]:
        result = func(url)
        if result:
            print(f"[+] Instagram via {func.__name__}")
            return result
        time.sleep(0.5)
    return None

# ==================== yt-dlp (TikTok + YouTube + الباقي) ====================
def download_ytdlp(url, user_id):
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
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        # إعدادات TikTok المُحسّنة
        if 'tiktok' in url:
            ydl_opts['extractor_args'] = {
                'tiktok': {
                    'api_hostname': 'api22-normal-c-useast2a.tiktokv.com',
                    'app_version': '34.0.5',
                    'manifest_app_version': '34.0.5',
                    'aid': '1988',
                }
            }
            ydl_opts['http_headers'] = {
                'User-Agent': 'com.zhiliaoapp.musically/2023400050 (Linux; U; Android 13; en_US; Pixel 7; Build/TQ3A.230805.001; Cronet/58.0.2991.0)',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        # إعدادات YouTube المُحسّنة
        elif 'youtube' in url or 'youtu.be' in url:
            ydl_opts['extractor_args'] = {
                'youtube': {'player_client': ['web', 'android', 'ios', 'tv_embedded']}
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
    kb = [
        [InlineKeyboardButton("📥 تنزيل فيديو", callback_data="dl"),
         InlineKeyboardButton("📜 تاريخي", callback_data="s_history")],
        [InlineKeyboardButton("📊 حالتي", callback_data="s_status"),
         InlineKeyboardButton("📋 المنصات", callback_data="s_platforms")],
        [InlineKeyboardButton("ℹ️ كيف أستخدم", callback_data="s_help"),
         InlineKeyboardButton("💡 اقتراح ميزة", callback_data="suggest")],
        [InlineKeyboardButton(f"🆘 الدعم @{SUPPORT_USER}",
                              url=f"https://t.me/{SUPPORT_USER}")],
    ]
    return InlineKeyboardMarkup(kb)

def kb_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="s_back")]])

def kb_admin():
    kb = [
        [InlineKeyboardButton("📊 إحصائيات", callback_data="a_stats"),
         InlineKeyboardButton("🏆 أفضل 10", callback_data="a_top")],
        [InlineKeyboardButton("📢 إرسال جماعي", callback_data="a_broadcast"),
         InlineKeyboardButton("🚫 حظر", callback_data="a_ban")],
        [InlineKeyboardButton("✅ رفع حظر", callback_data="a_unban"),
         InlineKeyboardButton("📥 آخر التنزيلات", callback_data="a_recent")],
        [InlineKeyboardButton("📊 حسب المنصة", callback_data="a_platforms"),
         InlineKeyboardButton("🔍 بحث مستخدم", callback_data="a_search")],
        [InlineKeyboardButton("💡 اقتراحات", callback_data="a_suggestions")],
    ]
    return InlineKeyboardMarkup(kb)

# ==================== /start ====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    add_user(uid, update.effective_user.username, update.effective_user.first_name)
    if is_banned(uid): return

    name = update.effective_user.first_name or "صديقي"
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

    bot_photo_id = context.bot_data.get('bot_photo_id')
    if bot_photo_id:
        try:
            await update.message.reply_photo(bot_photo_id, caption=caption,
                                             reply_markup=kb_services(),
                                             parse_mode='Markdown')
            return
        except:
            pass

    await update.message.reply_text(caption, reply_markup=kb_services(),
                                     parse_mode='Markdown',
                                     disable_web_page_preview=True)

# ==================== الأزرار ====================
async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    data = query.data

    if data.startswith("a_") and uid == ADMIN_ID:
        await handle_admin_cb(update, context, data)
        return

    if data == "s_back":
        name = query.from_user.first_name or "صديقي"
        caption = f"🔥 *أهلاً {name}*\n\n📥 *{BOT_NAME}*\n👇 أرسل رابطاً:"
        try:
            await query.message.delete()
        except:
            pass

        bot_photo_id = context.bot_data.get('bot_photo_id')
        if bot_photo_id:
            try:
                await query.message.chat.send_photo(bot_photo_id, caption=caption,
                                                    reply_markup=kb_services(),
                                                    parse_mode='Markdown')
                return
            except:
                pass
        await query.message.chat.send_message(caption, reply_markup=kb_services(),
                                              parse_mode='Markdown')
        return

    if data == "suggest":
        await query.message.chat.send_message(
            "💡 *اقتراح ميزة*\n\n📝 أرسل اقتراحك الآن:",
            parse_mode='Markdown')
        context.user_data['waiting_for_suggestion'] = True
        return

    if data == "dl":
        await query.message.chat.send_message("📥 أرسل الرابط الآن.", reply_markup=kb_back())
        return

    if data == "s_history":
        rows = db_query("SELECT url, platform, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10",
                        (uid,), True)
        if not rows:
            await query.message.chat.send_message("📜 لا يوجد تاريخ.", reply_markup=kb_back())
            return
        text = "📜 *آخر 10:*\n\n"
        for i, (url, plat, date) in enumerate(rows, 1):
            text += f"{i}. [{plat}] {date[:16]}\n"
        await query.message.chat.send_message(text, reply_markup=kb_back(),
                                              parse_mode='Markdown')
        return

    if data == "s_status":
        r = db_query("SELECT downloads, joined FROM users WHERE user_id=?", (uid,), True)
        dls = r[0][0] if r else 0
        joined = r[0][1] if r else ""
        text = f"📊 *حالتك*\n\n🆔 `{uid}`\n📥 تنزيلاتك: {dls}\n📅 {joined[:10]}"
        await query.message.chat.send_message(text, reply_markup=kb_back(),
                                              parse_mode='Markdown')
        return

    if data == "s_platforms":
        text = ("📋 *المنصات المدعومة:*\n\n"
                "• YouTube\n• TikTok\n• Instagram\n"
                "• Twitter / X\n• Facebook\n• Snapchat\n"
                "• Pinterest\n• Reddit\n• Telegram\n"
                "• Vimeo\n• Dailymotion\n• Twitch")
        await query.message.chat.send_message(text, reply_markup=kb_back(),
                                              parse_mode='Markdown')
        return

    if data == "s_help":
        text = "ℹ️ *كيف أستخدم:*\n\n1️⃣ أرسل رابط الفيديو.\n2️⃣ انتظر التنزيل."
        await query.message.chat.send_message(text, reply_markup=kb_back(),
                                              parse_mode='Markdown')
        return

# ==================== لوحة المطور ====================
async def handle_admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    kb_back_a = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="a_back")]])

    if data == "a_back":
        await query.message.chat.send_message("👑 لوحة المطور", reply_markup=kb_admin())
        return

    if data == "a_stats":
        users = db_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]
        dls = db_query("SELECT COUNT(*) FROM history", fetch=True)[0][0]
        b = db_query("SELECT COUNT(*) FROM users WHERE banned=1", fetch=True)[0][0]
        sug = db_query("SELECT COUNT(*) FROM suggestions", fetch=True)[0][0]
        await query.message.chat.send_message(
            f"📊 *إحصائيات*\n\n👥 {users}\n🚫 {b}\n📥 {dls}\n💡 {sug}",
            reply_markup=kb_back_a, parse_mode='Markdown')
        return

    if data == "a_top":
        rows = db_query("SELECT first_name, downloads FROM users ORDER BY downloads DESC LIMIT 10", fetch=True)
        text = "🏆 *أفضل 10:*\n\n"
        for i, (n, d) in enumerate(rows, 1):
            text += f"{i}. {n} — 📥{d}\n"
        await query.message.chat.send_message(text, reply_markup=kb_back_a, parse_mode='Markdown')
        return

    if data == "a_broadcast":
        await query.message.chat.send_message("✍️ أرسل الرسالة للجميع:")
        context.user_data['waiting_for_broadcast'] = True
        return

    if data == "a_ban":
        await query.message.chat.send_message("أرسل ID للحظر:")
        context.user_data['waiting_for_ban'] = True
        return

    if data == "a_unban":
        await query.message.chat.send_message("أرسل ID لرفع الحظر:")
        context.user_data['waiting_for_unban'] = True
        return

    if data == "a_recent":
        rows = db_query("SELECT user_id, platform, date FROM history ORDER BY id DESC LIMIT 15", fetch=True)
        text = "📥 *آخر 15:*\n\n"
        for u, p, d in rows:
            text += f"• {u} | {p} | {d[:16]}\n"
        await query.message.chat.send_message(text, reply_markup=kb_back_a, parse_mode='Markdown')
        return

    if data == "a_platforms":
        rows = db_query("SELECT platform, COUNT(*) FROM history GROUP BY platform ORDER BY COUNT(*) DESC", fetch=True)
        text = "📊 *حسب المنصة:*\n\n"
        for p, c in rows:
            text += f"• {p}: {c}\n"
        await query.message.chat.send_message(text, reply_markup=kb_back_a, parse_mode='Markdown')
        return

    if data == "a_search":
        await query.message.chat.send_message("أرسل ID للبحث:")
        context.user_data['waiting_for_search'] = True
        return

    if data == "a_suggestions":
        rows = db_query("SELECT first_name, username, message, date FROM suggestions ORDER BY id DESC LIMIT 15", fetch=True)
        if not rows:
            await query.message.chat.send_message("💡 لا اقتراحات.", reply_markup=kb_back_a)
            return
        text = "💡 *آخر 15 اقتراح:*\n\n"
        for i, (name, un, msg, date) in enumerate(rows, 1):
            text += f"{i}. *{name}* (@{un})\n   {msg[:80]}\n\n"
        await query.message.chat.send_message(text, reply_markup=kb_back_a, parse_mode='Markdown')
        return

# ==================== معالج الرسائل ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text: return
    text = message.text.strip()
    uid = message.from_user.id
    if is_banned(uid): return

    # اقتراح
    if context.user_data.get('waiting_for_suggestion'):
        context.user_data['waiting_for_suggestion'] = False
        username = message.from_user.username or "لا يوجد"
        first_name = message.from_user.first_name or "مستخدم"
        save_suggestion(uid, username, first_name, text)
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"💡 *اقتراح جديد*\n\n👤 {first_name}\n🆔 `{uid}`\n"
                f"📛 @{username}\n\n📝 {text}",
                parse_mode='Markdown')
        except: pass
        await message.reply_text("✅ تم إرسال اقتراحك!")
        return

    # broadcast
    if context.user_data.get('waiting_for_broadcast') and uid == ADMIN_ID:
        context.user_data['waiting_for_broadcast'] = False
        users = db_query("SELECT user_id FROM users WHERE banned=0", fetch=True)
        ok = fail = 0
        for (u,) in users:
            try:
                await context.bot.send_message(u, text)
                ok += 1
                time.sleep(0.05)
            except: fail += 1
        await message.reply_text(f"✅ {ok} | ❌ {fail}")
        return

    # ban
    if context.user_data.get('waiting_for_ban') and uid == ADMIN_ID:
        context.user_data['waiting_for_ban'] = False
        try:
            u = int(text)
            db_query("UPDATE users SET banned=1 WHERE user_id=?", (u,))
            await message.reply_text(f"🚫 {u}")
        except: await message.reply_text("❌")
        return

    # unban
    if context.user_data.get('waiting_for_unban') and uid == ADMIN_ID:
        context.user_data['waiting_for_unban'] = False
        try:
            u = int(text)
            db_query("UPDATE users SET banned=0 WHERE user_id=?", (u,))
            await message.reply_text(f"✅ {u}")
        except: await message.reply_text("❌")
        return

    # search
    if context.user_data.get('waiting_for_search') and uid == ADMIN_ID:
        context.user_data['waiting_for_search'] = False
        try:
            u = int(text)
            r = db_query("SELECT * FROM users WHERE user_id=?", (u,), True)
            if not r:
                await message.reply_text("❌")
                return
            row = r[0]
            await message.reply_text(f"👤 {row[2]}\n🆔 {row[0]}\n📥 {row[4]}\n🚫 {'نعم' if row[3] else 'لا'}")
        except: await message.reply_text("❌")
        return

    # كود المطور السري
    if text == ADMIN_SECRET and uid == ADMIN_ID:
        await message.reply_text("👑 *لوحة المطور*", reply_markup=kb_admin(),
                                  parse_mode='Markdown')
        return

    # رابط
    url = extract_url(text)
    if url:
        await handle_url(update, context, url)
        return

    if text.startswith('/'):
        return

    await message.reply_text("📌 أرسل رابط فيديو للتنزيل.")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    message = update.message
    uid = message.from_user.id
    add_user(uid, message.from_user.username, message.from_user.first_name)

    platform = detect_platform(url)
    wait = await message.reply_text(f"⏳ جارٍ التنزيل من {platform}...")

    result = download_media(url, uid)

    if not result:
        await wait.edit_text(f"❌ فشل التنزيل من {platform}\n\nجرب رابطاً آخر.")
        return

    title = result.get('title', '')[:100] if 'title' in result else ''
    caption = f"✅ تم التنزيل\n📌 {title}\n🌐 {platform}" if title else f"✅ تم التنزيل\n🌐 {platform}"

    try:
        if result['type'] == 'url_video':
            await message.reply_video(result['url'], caption=caption, supports_streaming=True)
        elif result['type'] == 'url_photo':
            await message.reply_photo(result['url'], caption=caption)
        elif result['type'] == 'file':
            ext = result['path'].split('.')[-1].lower()
            with open(result['path'], 'rb') as f:
                if ext == 'mp3':
                    await message.reply_audio(f, caption=caption)
                else:
                    await message.reply_video(f, caption=caption, supports_streaming=True)
            try: os.remove(result['path'])
            except: pass

        try:
            await wait.delete()
        except: pass

        inc_downloads(uid)
        log_history(uid, url, platform, title)
    except Exception as e:
        print(f"[send] {e}")
        try:
            await wait.edit_text(f"❌ خطأ: {e}")
        except: pass

# ==================== التشغيل ====================
async def post_init(application: Application):
    try:
        me = await application.bot.get_me()
        photos = await application.bot.get_user_profile_photos(me.id, limit=1)
        if photos.total_count > 0:
            application.bot_data['bot_photo_id'] = photos.photos[0][-1].file_id
            print("[+] Bot photo loaded")
    except Exception as e:
        print(f"[!] Bot photo: {e}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    print("=" * 60)
    print(f"  🔥 {BOT_NAME}")
    print("=" * 60)
    print(f"  🎬 FFmpeg: {FFMPEG_PATH}")
    print(f"  🍪 Cookies: {'✓' if os.path.exists(COOKIES_FILE) else '✗'}")
    print("=" * 60)

    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CallbackQueryHandler(cb_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("[+] Starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
