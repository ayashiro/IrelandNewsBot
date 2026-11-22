# 🇮🇪 Ireland News Discord Bot

アイルランドの主要ニュースメディアから最新のヘッドラインを毎日自動取得し、**Gemini API（`gemini-4-hydrogen`）** で自然な日本語に翻訳して Discord チャンネルへ投稿する Bot です。

Google Cloud（**Cloud Run Jobs + Cloud Scheduler + Secret Manager**）または **GitHub Actions** を使って、サーバーを常時起動せずに低コスト（無料枠中心）で毎日定時実行できます。

---

## 主な特徴

- **アイルランド主要3メディアを網羅**（RSSフィードから自動取得）
  - **RTÉ News**（アイルランド国営放送）
  - **The Irish Times**（主要全国紙）
  - **TheJournal.ie**（主要オンラインニュースメディア）
- **自然な日本語ヘッドライン翻訳**
  - Gemini API（`google-genai` SDK / JSON構造化出力）で全見出しを一括翻訳（1日1リクエスト）
- **見やすい Discord Embed 形式**
  - メディアごとに色分けされたカード形式で、記事リンク付きの日本語ヘッドラインを投稿
- **柔軟なタイムゾーン・スケジュール設定**
  - デフォルトでアイルランド時間（`Europe/Dublin`、夏時間・冬時間自動対応）の日付表示に対応

---

## アーキテクチャ（GCP 構成）

```text
Cloud Scheduler (毎日 08:00 Europe/Dublin)
        │  HTTP POST (OAuth)
        ▼
Cloud Run Jobs (ireland-news-bot)
   ├── Secret Manager から APIキー / Webhook URL を取得
   ├── アイルランド3メディアの RSS を取得
   ├── Gemini API (gemini-4-hydrogen) で日本語翻訳
   └── Discord Webhook へ Embed 投稿
```

---

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `main.py` | RSS取得・Gemini翻訳・Discord投稿を行うメインスクリプト |
| `requirements.txt` | Python 依存パッケージ一覧 |
| `Dockerfile` | Cloud Run Jobs 用コンテナ定義（Python 3.12-slim） |
| `deploy_gcp.sh` | GCP（Secret Manager / Cloud Run Jobs / Cloud Scheduler）一括デプロイスクリプト |
| `.github/workflows/daily_news.yml` | GitHub Actions で定期実行する場合のワークフロー定義 |
| `.env.example` | 環境変数のテンプレート |

---

## 環境変数

| 変数名 | 必須 | デフォルト値 | 説明 |
| --- | :---: | --- | --- |
| `GEMINI_API_KEY` | ✅ | - | Google AI Studio で発行した Gemini API キー |
| `DISCORD_WEBHOOK_URL` | ✅ | - | 投稿先 Discord チャンネルの Webhook URL |
| `GEMINI_MODEL` | - | `gemini-4-hydrogen` | 翻訳に使用する Gemini モデル ID |
| `HEADLINES_PER_SOURCE` | - | `5` | 1メディアあたりの取得件数 |
| `DISPLAY_TZ` | - | `Europe/Dublin` | 投稿メッセージ内の日付表示に使うタイムゾーン（例：`Asia/Tokyo`） |

---

## 事前準備

1. **Discord Webhook URL の取得**
   - 投稿したいサーバーの **サーバー設定** → **連携サービス** → **ウェブフック** → **新しいウェブフック** から投稿先チャンネルを選び、URLをコピーします。
2. **Gemini API キーの取得**
   - [Google AI Studio](https://aistudio.google.com/apikey) で API キーを作成します。

---

## 実行方法

### 方法 1：GCP（Cloud Run Jobs + Cloud Scheduler）で運用する（推奨）

#### Cloud Shell または `gcloud` CLI から一括デプロイ

```bash
chmod +x deploy_gcp.sh
export PROJECT_ID="あなたのGCPプロジェクトID"
export GEMINI_API_KEY="あなたのGemini APIキー"
export DISCORD_WEBHOOK_URL="あなたのDiscord Webhook URL"

# 任意：配信時刻やタイムゾーンを変更する場合
export SCHEDULE="0 8 * * *"
export TIME_ZONE="Europe/Dublin"   # 日本時間にする場合は "Asia/Tokyo"

./deploy_gcp.sh
```

#### 手動テスト実行

```bash
gcloud run jobs execute ireland-news-bot --region asia-northeast1 --wait
```

#### モデルや件数の設定だけ変更する

```bash
gcloud run jobs update ireland-news-bot \
  --region asia-northeast1 \
  --update-env-vars="GEMINI_MODEL=gemini-4-hydrogen,HEADLINES_PER_SOURCE=5"
```

---

### 方法 2：GitHub Actions で運用する（GCP 不要）

1. リポジトリの **Settings** → **Secrets and variables** → **Actions** に以下を登録：
   - `GEMINI_API_KEY`
   - `DISCORD_WEBHOOK_URL`
2. **Actions** タブ → **Daily Ireland News to Discord** → **Run workflow** で動作テスト
3. 配信時刻を変更したい場合は `.github/workflows/daily_news.yml` の `cron`（UTC基準）を編集します。

---

### 方法 3：ローカル環境でテスト実行する

```bash
python -m venv .venv
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# macOS / Linux:        source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# .env に GEMINI_API_KEY と DISCORD_WEBHOOK_URL を記入して実行
python main.py
```

---

## ライセンス

MIT License
