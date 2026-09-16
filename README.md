# CreatorOS v0.1 - Personal AI Daily Content Assistant

CreatorOS is a personal AI short-form vertical video assistant built on Django. It automates the generation of 9:16 vertical short videos (Shorts, Reels, TikTok) from simple user ideas or niche topics, renders real MP4 videos via FFmpeg, and delivers complete content packages directly to Telegram and Web History.

---

## 🌟 Key Capabilities

1. **Unified Content Service Pipeline**: Shared identically between Web Dashboard and Telegram Bot (`services/pipeline/service.py`).
2. **Structured AI Generation**: Produces validated JSON packages (Hook, Title, Script, Caption, Hashtags, Promotion Tips, Publish Time).
3. **Concept Expansion**: Automatically expands short user inputs (e.g. "dog video") into structured educational/engaging scripts.
4. **Real Vertical 9:16 MP4 Video Rendering**: Merges visual background image + gTTS MP3 audio + SRT subtitles into a 1080x1920 MP4 video via system FFmpeg.
5. **Telegram Bot Sync & Account Linking**: Secure `/start CODE` linking, bot commands (`/start`, `/create`, `/daily`, `/today`, `/history`, `/profile`, `/settings`, `/status`), and automated video delivery.
6. **Idempotent Daily Automation**: `python manage.py generate_daily_content` command with date checks & DB locks to prevent duplicate daily videos.
7. **Free-First & Provider Agnostic**: Supports Pollinations.ai free visuals, gTTS audio, built-in smart structured script engine, and BYOK (Bring Your Own Key) OpenAI integration.
8. **System Health Doctor**: Diagnostic command `python manage.py doctor` auditing Django, DB, Media, FFmpeg, FFprobe, gTTS, Pollinations, and Telegram API.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- FFmpeg (Installed on OS: `sudo apt install ffmpeg`)

### 2. Setup Virtual Environment & Dependencies
```bash
cd /home/linux/PycharmProjects/CreatorOS
python -m venv .venv
source .venv/bin/python
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` if desired:
```env
SECRET_KEY=django-insecure-creatoros-prod-key
DEBUG=True
ALLOWED_HOSTS=*
TELEGRAM_BOT_TOKEN=8173429381:AAH...
OPENAI_API_KEY=
```

### 4. Database Migrations
```bash
python manage.py migrate
```

### 5. System Health Check (Doctor)
Run the diagnostic command to verify system readiness:
```bash
python manage.py doctor
```

### 6. Run Web Dashboard
```bash
python manage.py runserver 8000
```
Open browser at `http://127.0.0.1:8000/`.

---

## 📱 Telegram Bot Commands

- `/start [CODE]` - Link Telegram account using 6-char code from Settings page
- `/create <idea>` - Generate a new vertical 9:16 video from user idea
- `/daily` - Trigger today's automated niche content video
- `/today` - Check status of today's generated posts
- `/history` - View recent post history
- `/profile` - View content profile preferences
- `/settings` - View account & Telegram connection status
- `/status` - Check generation & delivery status

To launch the Telegram bot polling runner:
```bash
python manage.py run_bot
```

---

## ⏰ Automated Daily Content Scheduler

To run idempotent daily content generation for all active users:
```bash
python manage.py generate_daily_content
```
*Can be scheduled via cron or systemd timer (e.g. `0 10 * * * python manage.py generate_daily_content`).*

---

## 🧪 Testing

Run the automated integration & unit test suite:
```bash
python manage.py test
```

---

## 🛡️ Security & Privacy
- Strict Multi-Tenancy & User Data Isolation (`request.user` enforced across all queries).
- Real Django Password Hashing & Authentication.
- Path traversal protection on media file download endpoints.
- Path traversal sanitization on FFmpeg subtitle file paths.
