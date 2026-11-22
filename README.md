# 🇮🇪 Ireland News Discord Bot

A lightweight automated bot that fetches the latest headlines from major Irish news outlets every day, translates them into natural Japanese using the **Gemini API (`gemini-4-hydrogen`)**, and posts them to a Discord channel via Webhook.

Runs serverlessly on **Google Cloud (Cloud Run Jobs + Cloud Scheduler + Secret Manager)** or **GitHub Actions** at minimal cost (largely within free tiers), with no always-on server required.

---

## Features

- **Covers 3 major Irish news outlets** (via RSS feeds):
  - **RTÉ News** (Ireland's national public service broadcaster)
  - **The Irish Times** (Ireland's leading national newspaper)
  - **TheJournal.ie** (major Irish online news publication)
- **Natural Japanese headline translation**:
  - Uses the official `google-genai` Python SDK with structured JSON output to translate all headlines in a single daily API call.
- **Clean Discord Embed layout**:
  - Posts color-coded embeds per news source with clickable links to each original article.
- **Timezone & schedule aware**:
  - Defaults to Ireland local time (`Europe/Dublin`, with automatic IST/GMT daylight saving support) for both scheduling and date headers.

---

## Architecture (Google Cloud)

```text
Cloud Scheduler (Daily 08:00 Europe/Dublin)
        │  HTTP POST (OAuth)
        ▼
Cloud Run Jobs (ireland-news-bot)
   ├── Loads API key & Webhook URL from Secret Manager
   ├── Fetches RSS feeds from 3 Irish news outlets
   ├── Translates headlines via Gemini API (gemini-4-hydrogen)
   └── Posts formatted embeds to Discord Webhook
```

---

## Project Structure

| File | Description |
| --- | --- |
| `main.py` | Main script for fetching RSS feeds, translating with Gemini, and posting to Discord |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container image definition for Cloud Run Jobs (`python:3.12-slim`) |
| `deploy_gcp.sh` | One-shot deployment script for Secret Manager, Cloud Run Jobs, and Cloud Scheduler |
| `.github/workflows/daily_news.yml` | GitHub Actions workflow for scheduled daily runs |
| `.env.example` | Environment variable template |

---

## Environment Variables

| Variable | Required | Default | Description |
| --- | :---: | --- | --- |
| `GEMINI_API_KEY` | ✅ | - | Gemini API key from Google AI Studio |
| `DISCORD_WEBHOOK_URL` | ✅ | - | Target Discord channel Webhook URL |
| `GEMINI_MODEL` | - | `gemini-4-hydrogen` | Gemini model ID used for translation |
| `HEADLINES_PER_SOURCE` | - | `5` | Number of headlines to fetch per news outlet |
| `DISPLAY_TZ` | - | `Europe/Dublin` | IANA timezone for the date shown in Discord posts (e.g. `Asia/Tokyo`) |

---

## Prerequisites

1. **Discord Webhook URL**
   - In your Discord server, go to **Server Settings** → **Integrations** → **Webhooks** → **New Webhook**, choose the target text channel, and copy the Webhook URL.
2. **Gemini API Key**
   - Create an API key in [Google AI Studio](https://aistudio.google.com/apikey).

---

## Deployment & Usage

### Option 1: Google Cloud (Cloud Run Jobs + Cloud Scheduler) — Recommended

#### Deploy via Cloud Shell or `gcloud` CLI

```bash
chmod +x deploy_gcp.sh
export PROJECT_ID="your-gcp-project-id"
export GEMINI_API_KEY="your-gemini-api-key"
export DISCORD_WEBHOOK_URL="your-discord-webhook-url"

# Optional: customize schedule and timezone
export SCHEDULE="0 8 * * *"
export TIME_ZONE="Europe/Dublin"   # Use "Asia/Tokyo" for JST

./deploy_gcp.sh
```

#### Run a manual test execution

```bash
gcloud run jobs execute ireland-news-bot --region asia-northeast1 --wait
```

#### Update model or headline count without rebuilding

```bash
gcloud run jobs update ireland-news-bot \
  --region asia-northeast1 \
  --update-env-vars="GEMINI_MODEL=gemini-4-hydrogen,HEADLINES_PER_SOURCE=5"
```

---

### Option 2: GitHub Actions (No GCP Required)

1. Go to your repository's **Settings** → **Secrets and variables** → **Actions** and add:
   - `GEMINI_API_KEY`
   - `DISCORD_WEBHOOK_URL`
2. Open the **Actions** tab → **Daily Ireland News to Discord** → **Run workflow** to test.
3. To change the delivery time, edit the UTC `cron` schedule in `.github/workflows/daily_news.yml`.

---

### Option 3: Run Locally

```bash
python -m venv .venv
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# macOS / Linux:        source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Fill in GEMINI_API_KEY and DISCORD_WEBHOOK_URL in .env, then run:
python main.py
```

---

## License

MIT License
