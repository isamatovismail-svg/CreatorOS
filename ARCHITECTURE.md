# CreatorOS Architecture & System Manifesto

Welcome to **CreatorOS** — an enterprise-grade, modular SaaS platform for AI-driven automated content generation, scheduling, and distribution.

---

## 1. Core Project Principles (Принципы Проекта)

Every feature and contribution to CreatorOS **MUST** adhere to the following principles:

1. **Free/Freemium MVP First (Запуск с минимальными затратами)**
   - Always leverage zero-cost or freemium solutions first (e.g. Pollinations.ai, Edge-TTS, HuggingFace, Free LLM tiers). Paid providers are only suggested when freemium limits are insufficient.

2. **Zero Vendor Lock-in (Никакой зависимости от одного AI-сервиса)**
   - No AI model, TTS service, or social media network is hardcoded into the system core. Everything connects via abstract adapter interfaces (`BaseLLMProvider`, `BaseImageProvider`, `BaseTTSProvider`).

3. **Unified Integration Layer (Единый слой интеграций)**
   - Core pipeline logic remains standard regardless of which AI provider is generating the script, image, voiceover, or video. Switching providers requires zero core code changes.

4. **Bring Your Own Key (BYOK) Support (Собственные API-ключи)**
   - Users can plug in their own OpenAI, Groq, Gemini, Replicate, or ElevenLabs API keys in their profile to unlock high quotas and custom models.

5. **Plug & Play Core + Plugins (Модульность ядро + плагины)**
   - Any service (AI provider, video generator, or social poster) can be plugged in or swapped out without modifying the core Django models or business logic.

6. **Guaranteed Telegram Fallback (Всегда функциональный фоллбэк)**
   - Because TikTok, Instagram, or YouTube APIs can restrict automated posting or token expiration may occur, the system **ALWAYS** includes a automatic fallback mechanism that delivers the complete post package (MP4 video/image + text copy + hashtags) directly to the user's Telegram chat for 1-click manual upload.

7. **Architecture Explanation Before Code (Объяснение перед кодом)**
   - Before introducing any major feature, developers must explain the system architecture, present the directory structure, evaluate free vs. paid alternatives, and highlight risks with mitigation options.

---

## 2. Directory & Component Blueprint

```
/home/linux/PycharmProjects/CreatorOS/
├── ARCHITECTURE.md                  # Master System Architecture & Principles Manifesto
├── manage.py                        # Django CLI Management
├── requirements.txt                 # Project Dependencies
├── .gitignore                       # Git exclusion rules
│
├── creatoros/                       # Project Core Configuration
│   ├── settings.py                  # Environment & App Registries
│   └── urls.py                      # Root URL Routing
│
├── core/                            # Core Django App (Data & Dashboard UI)
│   ├── models.py                    # UserProfile (BYOK), ContentPost, ContentTopic, SocialAccount, SystemLog
│   ├── views.py                     # Dashboard Metrics & Post Generation Handlers
│   ├── admin.py                     # Admin Panel Site Controls
│   └── tests.py                     # Automated Unit & Integration Tests
│
├── services/                        # Modular Services Layer (Plug & Play)
│   ├── ai_provider/                 # Dynamic AI Provider Manager
│   │   ├── base.py                  # Abstract Provider Classes (LLM, Image, TTS)
│   │   ├── ai_manager.py            # Registry Factory & Priority Fallback Chain
│   │   └── adapters/                # Concrete Adapters (Default LLM, Pollinations, Edge-TTS, OpenAI)
│   ├── pipeline/                    # Content Generation Pipeline Engine
│   │   └── generator.py             # Script -> Voice -> Visuals -> Caption synthesis
│   └── posting/                     # Social Media API Posting Adapters
│
├── bot/                             # Telegram Bot & Fallback Manager
│   ├── bot_runner.py                # Interactive Bot Commands (/start, /generate, /topics, /status)
│   └── fallback_manager.py          # Direct Telegram Delivery Engine for Manual Upload
│
├── templates/                       # Responsive Premium Dark-Mode Templates
│   ├── base.html                    # Layout, Navigation Sidebar & Top Header
│   └── core/index.html              # Live Pipeline Dashboard & Quick Post Generator
│
└── static/                          # Static Assets & Design System
    └── css/main.css                 # Custom CSS Design System Tokens & Animations
```

---

## 3. Provider Agnostic Architecture (AI Provider Layer)

The `AIProviderManager` uses factory patterns and fallback chains to guarantee uptime:

```
[Content Pipeline Request]
         │
         ▼
 ┌──────────────┐      BYOK Key Present?      ┌──────────────────────┐
 │ AI Manager   │ ───────────────► Yes ─────► │ User Custom Provider │ (OpenAI / Gemini / ElevenLabs)
 └──────────────┘                             └──────────────────────┘
         │
         │ No / API Error
         ▼
 ┌──────────────────────┐
 │ Freemium Provider    │ (Pollinations.ai / Edge-TTS / Free Engine)
 └──────────────────────┘
```

---

## 4. Security, Backups & Scaling Architecture

1. **Security & BYOK Protection**:
   - User API keys are stored with field-level encryption or secure configuration attributes.
   - All credentials, tokens, and secrets are passed via environment variables or encrypted Django user profile fields.

2. **Audit Logging & System Resilience**:
   - All pipeline steps, API failures, token expirations, and Telegram fallback deliveries log events to `SystemLog`.

3. **Scaling to Thousands of Users**:
   - Long-running video synthesis jobs execute asynchronously via background task queues (Celery / RQ) to avoid blocking main web loopers.
   - Media assets are structured under `media/posts/{id}/` for easy migration to cloud object storage (S3 / DigitalOcean Spaces).

4. **Automated Database Backups**:
   - Database dumps (`db.sqlite3` / PostgreSQL snapshots) are scheduled periodically to prevent data loss.

---

## 5. Summary of Freemium vs. Paid Upgrades

| Service Component | Freemium / Free Option (MVP) | Paid Upgrade Option (Scale) |
|---|---|---|
| **Script LLM** | Default Fallback Engine / Free Tiers | OpenAI GPT-4o / Groq Llama-3 / Claude 3.5 |
| **Voice TTS** | Edge-TTS / System Synthesizer | ElevenLabs / Play.ht |
| **Image / Visuals** | Pollinations.ai (Free 8K) | Midjourney API / Replicate SDXL |
| **Distribution** | Telegram Bot Manual Upload Fallback | Official TikTok / Instagram Graph API |
