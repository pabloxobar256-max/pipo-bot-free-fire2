#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 𝑷𝑰𝑷𝑶  𝑫𝑶𝑾𝑵𝑳𝑶𝑨𝑫 — نسخة مجانية جاهزة لـ Render

import os
import re
import time
import shutil
import sqlite3
import subprocess
import threading
from datetime import datetime

import telebot
from telebot import types
from flask import Flask
import yt_dlp
import instaloader

# ==================== الإعدادات ====================
BOT_TOKEN = "8819449250:AAHkz6pfTyUTAGZgipCjQvl2VH4CreP7Wp0"
ADMIN_ID = 8050958688
SUPPORT_USER = "amirx_xpipo"
BOT_NAME = "𝑷𝑰𝑷𝑶  𝑫𝑶𝑾𝑵𝑳𝑶𝑨𝑫"
ADMIN_SECRET = "830714pipo"

DOWNLOAD_DIR = "downloads"
DB_FILE = "pipo_bot.db"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== FFmpeg ====================
_ff = shutil.which("ffmpeg")
if _ff:
    FFMPEG_PATH = _ff
    print(f"[+] FFmpeg: {FFMPEG_PATH}")
else:
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"[+] FFmpeg (imageio): {FFMPEG_PATH}")
    except Exception:
        FFMPEG_PATH = "ffmpeg"
        print("[!] FFmpeg غير متوفر")

# ==================== Flask (للـ Render) ====================
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
    c.execute('''CREATE TABLE IF NOT EXISTS pending (
        user_id INTEGER PRIMARY KEY,
        url TEXT, platform TEXT,
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

def save_pending(uid, url, platform):
    db_query("INSERT OR REPLACE INTO pending (user_id, url, platform) VALUES (?, ?, ?)",
             (uid, url, platform))

def get_pending(uid):
    r = db_query("SELECT url, platform FROM pending WHERE user_id=?", (uid,), True)
    return (r[0][0], r[0][1]) if r else (None, None)

def clear_pending(uid):
    db_query("DELETE FROM pending WHERE user_id=?", (uid,))

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
def download_ytdlp(url, user_id, audio_only=False, quality='best'):
    try:
        platform = detect_platform(url)
        safe_id = f"{user_id}_{int(time.time())}"
        out_tmpl = os.path.join(DOWNLOAD_DIR, f"{safe_id}.%(ext)s")

        if audio_only:
            fmt = 'bestaudio/best'
        elif quality == '2k':
            fmt = ('bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/'
                   'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best')
        elif quality == 'hd':
            fmt = ('bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/'
                   'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best')
        else:
            fmt = 'best[ext=mp4]/best'

        ydl_opts = {
            'outtmpl': out_tmpl, 'quiet': True, 'no_warnings': True,
            'format': fmt,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'geo_bypass': True, 'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'retries': 3, 'fragment_retries': 3,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['hls', 'dash'],
                }
            },
        }

        if audio_only:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')[:80]
            for ext in ['mp4', 'mp3', 'webm', 'mkv', 'm4a']:
                path = os.path.join(DOWNLOAD_DIR, f"{safe_id}.{ext}")
                if os.path.exists(path):
                    return {'path': path, 'title': title, 'platform': platform}
        return None
    except Exception as e:
        print(f"[ytdlp] {e}")
        return None

def improve_video_quality(input_path, output_path):
    try:
        cmd = [FFMPEG_PATH, '-y', '-i', input_path,
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
               '-vf', 'scale=iw*1.5:ih*1.5:flags=lanczos,unsharp=5:5:0.8:3:3:0.4',
               '-c:a', 'aac', '-b:a', '192k', output_path]
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        if r.returncode == 0 and os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"[ffmpeg] {e}")
        return None

def download_instagram(url, user_id):
    try:
        shortcode = url.strip('/').split('/')[-1].split('?')[0]
        L = instaloader.Instaloader(
            dirname_pattern=os.path.join(DOWNLOAD_DIR, f"ig_{user_id}"),
            filename_pattern="{shortcode}",
            download_video_thumbnails=False, save_metadata=False,
        )
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        if post.is_video:
            L.download_post(post, target=f"ig_{user_id}")
            exp = os.path.join(DOWNLOAD_DIR, f"ig_{user_id}", f"{shortcode}.mp4")
            if os.path.exists(exp):
                return {'type': 'video', 'path': exp,
                        'title': (post.caption[:80] if post.caption else 'Video')}
        else:
            L.download_post(post, target=f"ig_{user_id}")
            exp = os.path.join(DOWNLOAD_DIR, f"ig_{user_id}", f"{shortcode}.jpg")
            if os.path.exists(exp):
                return {'type': 'photo', 'path': exp, 'title': 'Photo'}
        return None
    except Exception as e:
        print(f"[instagram] {e}")
        return None

def download_media(url, user_id, audio_only=False, quality='best'):
    platform = detect_platform(url)
    if platform == 'Instagram':
        r = download_instagram(url, user_id)
        if r: return r
    r = download_ytdlp(url, user_id, audio_only=audio_only, quality=quality)
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
        types.InlineKeyboardButton("📥 تنزيل فيديو", callback_data="s_video"),
        types.InlineKeyboardButton("🎵 استخراج صوت", callback_data="s_audio"),
    )
    kb.add(
        types.InlineKeyboardButton("🎬 جودة HD", callback_data="s_hd"),
        types.InlineKeyboardButton("🔥 جودة 2K", callback_data="s_2k"),
    )
    kb.add(
        types.InlineKeyboardButton("📜 تاريخي", callback_data="s_history"),
        types.InlineKeyboardButton("📊 حالتي", callback_data="s_status"),
    )
    kb.add(
        types.InlineKeyboardButton("📋 قائمة المنصات", callback_data="s_platforms"),
        types.InlineKeyboardButton("ℹ️ كيف أستخدم", callback_data="s_help"),
    )
    kb.add(types.InlineKeyboardButton(f"🆘 الدعم @{SUPPORT_USER}",
                                       url=f"https://t.me/{SUPPORT_USER}"))
    return kb

def kb_quality_for_url():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📥 عادي", callback_data="q_best"),
        types.InlineKeyboardButton("🎬 HD 1080p", callback_data="q_hd"),
    )
    kb.add(
        types.InlineKeyboardButton("🔥 2K محسّن", callback_data="q_2k"),
        types.InlineKeyboardButton("🎵 صوت MP3", callback_data="q_mp3"),
    )
    kb.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="q_cancel"))
    return kb

def kb_back():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع للخدمات", callback_data="s_back"))
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
    return kb

# ==================== /start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    add_user(uid, message.from_user.username, message.from_user.first_name)
    if is_banned(uid): return

    name = message.from_user.first_name or "صديقي"
    text = (
        f"🔥 *أهلاً {name}*\n\n"
        f"📥 *{BOT_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ بوت تنزيلات مجاني بالكامل\n"
        f"✅ يدعم 15+ منصة\n"
        f"🎵 صوت • 🎬 HD • 🔥 2K\n"
        f"♾️ بلا حدود\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 اختر خدمة، أو أرسل رابطاً مباشرة:"
    )
    bot.send_message(message.chat.id, text, reply_markup=kb_services(),
                     parse_mode='Markdown', disable_web_page_preview=True)

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
        text = (
            f"🔥 *أهلاً {name}*\n\n"
            f"📥 *{BOT_NAME}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ بوت تنزيلات مجاني بالكامل\n"
            f"👇 اختر خدمة، أو أرسل رابطاً مباشرة:"
        )
        try:
            bot.edit_message_text(text, chat_id=call.message.chat.id,
                                  message_id=call.message.message_id,
                                  reply_markup=kb_services(),
                                  parse_mode='Markdown',
                                  disable_web_page_preview=True)
        except:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=kb_services(),
                             parse_mode='Markdown',
                             disable_web_page_preview=True)
        bot.answer_callback_query(call.id, "🏠")
        return

    if data == "s_video":
        bot.answer_callback_query(call.id, "📥")
        bot.send_message(call.message.chat.id,
            "📥 *تنزيل فيديو*\n\nأرسل الرابط الآن.",
            parse_mode='Markdown', reply_markup=kb_back())
        return
    if data == "s_audio":
        bot.answer_callback_query(call.id, "🎵")
        bot.send_message(call.message.chat.id,
            "🎵 *استخراج صوت*\n\nأرسل الرابط واختر (صوت MP3).",
            parse_mode='Markdown', reply_markup=kb_back())
        return
    if data == "s_hd":
        bot.answer_callback_query(call.id, "🎬")
        bot.send_message(call.message.chat.id,
            "🎬 *HD 1080p*\n\nأرسل الرابط واختر (HD).",
            parse_mode='Markdown', reply_markup=kb_back())
        return
    if data == "s_2k":
        bot.answer_callback_query(call.id, "🔥")
        bot.send_message(call.message.chat.id,
            "🔥 *2K محسّن*\n\nأرسل الرابط واختر (2K).",
            parse_mode='Markdown', reply_markup=kb_back())
        return
    if data == "s_history":
        rows = db_query("SELECT url, platform, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10",
                        (uid,), True)
        if not rows:
            bot.answer_callback_query(call.id, "📜 فارغ")
            bot.send_message(call.message.chat.id, "📜 لا يوجد تاريخ بعد.",
                             reply_markup=kb_back())
            return
        text = "📜 *آخر 10 تنزيلات:*\n\n"
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
        text = (
            f"📊 *حالتك*\n\n"
            f"🆔 `{uid}`\n"
            f"📥 تنزيلاتك: {dls}\n"
            f"📅 انضممت: {joined[:10]}\n"
            f"♾️ الحساب: مجاني بلا حدود"
        )
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
        text = (
            "ℹ️ *كيف أستخدم البوت:*\n\n"
            "1️⃣ أرسل رابط الفيديو.\n"
            "2️⃣ اختر الجودة.\n"
            "3️⃣ انتظر التنزيل."
        )
        bot.answer_callback_query(call.id, "ℹ️")
        bot.send_message(call.message.chat.id, text, reply_markup=kb_back(),
                         parse_mode='Markdown')
        return

    # ---- خيارات الجودة ----
    if data.startswith("q_"):
        if data == "q_cancel":
            clear_pending(uid)
            bot.answer_callback_query(call.id, "❌ تم الإلغاء")
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            return

        url, platform = get_pending(uid)
        if not url:
            bot.answer_callback_query(call.id, "❌ انتهت الصلاحية", show_alert=True)
            return

        quality_map = {
            "q_best": ("best", False, "📥 عادي"),
            "q_hd": ("hd", False, "🎬 HD"),
            "q_2k": ("2k", False, "🔥 2K"),
            "q_mp3": ("best", True, "🎵 MP3"),
        }
        quality, audio_only, label = quality_map[data]

        bot.answer_callback_query(call.id, f"⏳ {label}")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        chat_id = call.message.chat.id
        wait = bot.send_message(chat_id, f"⏳ جارٍ التنزيل من {platform} — {label}...")

        result = download_media(url, uid, audio_only=audio_only, quality=quality)

        if not result:
            bot.edit_message_text(
                f"❌ فشل التنزيل من {platform}\n\nجرب رابطاً آخر.",
                chat_id=chat_id, message_id=wait.message_id)
            clear_pending(uid)
            return

        if quality == '2k' and result['type'] == 'video' and FFMPEG_PATH != "ffmpeg":
            bot.edit_message_text("🔥 جارٍ تحسين الجودة إلى 2K...",
                                  chat_id=chat_id, message_id=wait.message_id)
            improved = os.path.join(DOWNLOAD_DIR, f"2k_{int(time.time())}.mp4")
            new_path = improve_video_quality(result['path'], improved)
            if new_path:
                try: os.remove(result['path'])
                except: pass
                result['path'] = new_path

        title = result.get('title', '')[:100]
        caption = f"✅ تم التنزيل\n📌 {title}\n🌐 {platform}\n🎯 {label}"

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
            clear_pending(uid)
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ: {e}", chat_id=chat_id, message_id=wait.message_id)
        return

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
        today = datetime.now().strftime('%Y-%m-%d')
        tu = db_query("SELECT COUNT(*) FROM users WHERE joined LIKE ?", (f"{today}%",), True)[0][0]
        td = db_query("SELECT COUNT(*) FROM history WHERE date LIKE ?", (f"{today}%",), True)[0][0]
        b = db_query("SELECT COUNT(*) FROM users WHERE banned=1", fetch=True)[0][0]
        bot.answer_callback_query(call.id, "📊")
        bot.send_message(call.message.chat.id,
            f"📊 *إحصائيات*\n\n👥 {users}\n🚫 {b}\n📥 {dls}\n\n📅 اليوم: 👤{tu} | 📥{td}",
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
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل الرسالة:")
        bot.register_next_step_handler(msg, do_broadcast)
    elif data == "a_ban":
        bot.answer_callback_query(call.id, "🚫")
        msg = bot.send_message(call.message.chat.id, "أرسل ID:")
        bot.register_next_step_handler(msg, do_ban)
    elif data == "a_unban":
        bot.answer_callback_query(call.id, "✅")
        msg = bot.send_message(call.message.chat.id, "أرسل ID:")
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
        msg = bot.send_message(call.message.chat.id, "أرسل ID:")
        bot.register_next_step_handler(msg, do_search)

def do_broadcast(msg):
    if msg.from_user.id != ADMIN_ID: return
    users = db_query("SELECT user_id FROM users WHERE banned=0", fetch=True)
    ok = fail = 0
    for (u,) in users:
        try:
            bot.send_message(u, msg.text); ok += 1; time.sleep(0.05)
        except:
            fail += 1
    bot.reply_to(msg, f"✅ {ok} | ❌ {fail}")

def do_ban(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        db_query("UPDATE users SET banned=1 WHERE user_id=?", (u,))
        bot.reply_to(msg, f"🚫 {u}")
    except:
        bot.reply_to(msg, "❌")

def do_unban(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        db_query("UPDATE users SET banned=0 WHERE user_id=?", (u,))
        bot.reply_to(msg, f"✅ {u}")
    except:
        bot.reply_to(msg, "❌")

def do_search(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        u = int(msg.text.strip())
        r = db_query("SELECT * FROM users WHERE user_id=?", (u,), True)
        if not r:
            bot.reply_to(msg, "❌")
            return
        row = r[0]
        bot.reply_to(msg,
            f"👤 {row[2]}\n🆔 {row[0]}\n📥 {row[4]}\n🚫 {'نعم' if row[3] else 'لا'}")
    except:
        bot.reply_to(msg, "❌")

# ==================== الكود السري ====================
@bot.message_handler(func=lambda m: m.text == ADMIN_SECRET)
def secret_admin(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "👑 *لوحة المطور*\n\nاختر:",
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

    save_pending(uid, url, platform)

    text = (
        f"🎬 *الرابط مستلم*\n\n"
        f"🌐 المنصة: {platform}\n"
        f"🔗 `{url[:60]}...`\n\n"
        f"👇 *اختر الجودة:*"
    )
    bot.send_message(chat_id, text, reply_markup=kb_quality_for_url(),
                     parse_mode='Markdown', disable_web_page_preview=True)

# ==================== رسائل أخرى ====================
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video'])
def handle_other(message):
    if message.text and message.text.startswith('/'):
        return
    bot.reply_to(message, "📌 أرسل رابط فيديو للتنزيل، أو اضغط /start")

# ==================== التشغيل ====================
if __name__ == '__main__':
    # تشغيل Flask للمنفذ (Render)
    threading.Thread(target=run_flask, daemon=True).start()
    print("=" * 60)
    print(f"  🔥 {BOT_NAME} — يعمل على Render")
    print("=" * 60)
    print(f"  🎬 FFmpeg: {FFMPEG_PATH}")
    print("=" * 60)
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
