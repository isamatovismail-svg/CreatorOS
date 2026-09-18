# CreatorOS - Personal AI Daily Content Assistant & Multi-Provider Video Platform

CreatorOS is an enterprise-grade personal AI short-form vertical video platform built on Django and Python. It automates the end-to-end production of 9:16 vertical short videos (Shorts, Reels, TikTok) from simple user ideas or daily scheduled niche topics, performs scene breakdowns, orchestrates multi-provider AI video generation, validates real MP4 video outputs via FFprobe, and delivers complete content packages to Telegram and Web History.

---

## 🌟 Key Capabilities & Features

1. **Google OAuth 2.0 & Multi-Account Management**: Standard "Continue with Google" OAuth 2.0 login. Connect multiple Google accounts under User Profile with status tracking, strictly respecting provider terms and avoiding automated rate-limit rotation.
2. **Unified Content Service Pipeline**: Shared identically between Web Dashboard, Scheduler, and Telegram Bot (`services/pipeline/service.py`).
3. **AI Provider Manager & Router (`services/ai/`)**: Multi-provider registry (`base.py`, `registry.py`, `router.py`, `providers/`) supporting Google AI (Veo / Gemini), OpenAI (Sora / GPT), Runway Gen-3, and Local Fallback Engine.
4. **Free-First Mode & User Preferences**: Prioritizes free & local engines by default (`allow_paid_generation=False`), respecting user preferred provider ordering and BYOK keys.
5. **Real MP4 Video Inspection & Validation (`services/video/validator.py`)**: Automates FFprobe checks for MP4 container, video stream, audio stream, resolution, and minimum duration. Never creates fake or corrupt MP4 files.
6. **Quota Tracking & Waiting States (`AIProviderAccount` & `AIUsage`)**: Classifies provider quota responses. Sets post status to `WAITING_FOR_QUOTA` when quota limits are reached without breaking the application.
7. **Telegram Bot Integration & Delivery**: Account linking via `/start CODE`, bot commands (`/start`, `/create`, `/daily`, `/today`, `/history`, `/profile`, `/settings`, `/status`), and automated video delivery.
8. **Idempotent Daily Automation**: `python manage.py generate_daily_content` command with date checks to prevent duplicate daily video generation per user.
9. **Unified Launcher**: `python manage.py run_creatoros` launches Django Web Server, Telegram Bot Polling, and Daily Content Scheduler concurrently in one terminal with graceful Ctrl+C shutdown.
10. **System Health Doctor**: Diagnostic command `python manage.py doctor` auditing Django, DB, Media, FFmpeg, FFprobe, gTTS, Pollinations, Google OAuth, OpenAI, and Telegram API without exposing raw credentials.

---

## 🎬 Video Provider Architecture

CreatorOS strictly separates **Real Moving Video Providers** from **Local Fallback Engines**.

### REAL VIDEO PROVIDERS

1. **Google AI (Veo / Gemini)**
   - **Status:** Implemented (`google-genai` official SDK)
   - **Model:** `veo-2.0-generate-001` (video clips) & `gemini-2.5-flash` (structured script)
   - **Credential Required:** `GOOGLE_VEO_API_KEY` or `GEMINI_API_KEY`
   - **Pricing:** Paid API (Requires Google Cloud / Google AI Studio billing)
   - **Output:** 9:16 vertical MP4 video clips concatenated into final 1080x1920 MP4
   - **Quota Behavior:** 429 / ResourceExhausted updates `AIProviderAccount.quota_status = 'EXHAUSTED'` and sets post to `WAITING_FOR_QUOTA`

2. **OpenAI (Sora / GPT)**
   - **Status:** Adapter / Placeholder
   - **Credential Required:** `OPENAI_API_KEY`
   - **Pricing:** Paid API
   - **Output:** 9:16 vertical MP4 video
   - **Quota Behavior:** Quota error sets post to `WAITING_FOR_QUOTA`

3. **Runway Gen-3**
   - **Status:** Adapter / Placeholder
   - **Credential Required:** `RUNWAY_API_KEY`
   - **Pricing:** Paid API
   - **Output:** 9:16 vertical MP4 video
   - **Quota Behavior:** Quota error sets post to `WAITING_FOR_QUOTA`

### LOCAL FALLBACK

1. **Local Fallback Engine**
   - **Status:** Fully Functional
   - **Credential Required:** None
   - **Pricing:** Free local generation
   - **Output:** 9:16 vertical MP4 video (Pollinations visual background + gTTS voiceover + FFmpeg renderer + SRT subtitles)
   - **Usage:** Used automatically when `allow_paid_generation=False` or when no paid API provider is configured. Displays message: `"No free real-video provider is currently configured. Using Local Fallback Engine."`

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- FFmpeg & FFprobe (Installed on OS: `sudo apt install ffmpeg`)

### 2. Setup Virtual Environment & Dependencies
```bash
cd /home/linux/PycharmProjects/CreatorOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env`:
```env
SECRET_KEY=django-insecure-creatoros-prod-key
DEBUG=True
ALLOWED_HOSTS=*

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback/

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN=8173429381:AAH...

# AI Provider Keys
OPENAI_API_KEY=sk-...
GOOGLE_VEO_API_KEY=...
RUNWAY_API_KEY=...
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

### 6. Run Unified Launcher
To launch Django Web Server, Telegram Bot Worker, and Daily Scheduler together:
```bash
python manage.py run_creatoros
```
*Or run individual services:*
- Web Dashboard: `python manage.py runserver 8000`
- Telegram Bot: `python manage.py run_bot`
- Daily Scheduler: `python manage.py generate_daily_content`

---

## 🧪 Testing

Run the automated integration & unit test suite:
```bash
python manage.py test
```

---

## 🛡️ Security & Privacy
- Zero Google Password Storage: Authenticates exclusively via Google OAuth 2.0.
- Token Protection: OAuth access/refresh tokens are stored securely and excluded from logs and HTML output.
- Strict Multi-Tenancy & User Data Isolation (`request.user` enforced across all queries).
- Real Django Password Hashing & Authentication.
- Path traversal protection on media file streaming endpoints (`/post/<id>/download/<type>/`).

