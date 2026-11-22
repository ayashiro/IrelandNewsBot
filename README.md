# 🇮🇪 Ireland News Discord Bot

アイルランドの主要ニュースメディアから最新のヘッドラインを取得し、Gemini APIで自然な日本語に翻訳して、毎日決まった時間にDiscordへ自動投稿するBotです。

## 取得するニュース元
- **RTÉ News**（アイルランド国営放送）
- **The Irish Times**（アイルランドを代表する全国紙）
- **TheJournal.ie**（主要オンラインニュースメディア）

---

## 事前準備（共通）

### 1. Discord Webhook URLを取得する
1. 投稿したいDiscordチャンネルの **チャンネルの編集（歯車アイコン）** を開く
2. **連携サービス** → **ウェブフック** → **新しいウェブフック** をクリック
3. 名前（例：`Ireland News`）を設定し、**ウェブフックURLをコピー** する

### 2. Gemini APIキーを取得する
1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセスしてGoogleアカウントでログイン
2. **APIキーを作成** をクリックしてキーをコピーする（無料枠あり）

---

## 方法A：GCP（Cloud Run Jobs + Cloud Scheduler）で動かす

GCPのブラウザ画面にある **Cloud Shell** を使えば、PCに `gcloud` CLI を入れずにそのままデプロイできます。

1. [Google Cloud Console](https://console.cloud.google.com/) を開き、使用するプロジェクトを選択（請求先アカウントが紐づいている必要があります）
2. 右上の **Cloud Shell をアクティブにする（`>_` アイコン）** をクリック
3. Cloud Shell のメニュー（`⋮` → **アップロード**）からこのプロジェクトのファイル（`main.py`, `requirements.txt`, `Dockerfile`, `.dockerignore`, `deploy_gcp.sh`）をアップロードする（または GitHub 経由で `git clone`）
4. Cloud Shell で以下を実行する：

```bash
chmod +x deploy_gcp.sh
export PROJECT_ID="あなたのGCPプロジェクトID"
export GEMINI_API_KEY="あなたのGemini APIキー"
export DISCORD_WEBHOOK_URL="あなたのDiscord Webhook URL"

# 任意: 配信時刻やタイムゾーンを変える場合
# export SCHEDULE="0 8 * * *"
# export TIME_ZONE="Asia/Tokyo"   # アイルランド時間なら "Europe/Dublin"

./deploy_gcp.sh
```

5. デプロイ完了後、以下でテスト実行してDiscordに届くか確認する：

```bash
gcloud run jobs execute ireland-news-bot --region asia-northeast1 --wait
```

※ Windows PCから直接デプロイしたい場合は、[Google Cloud CLI](https://cloud.google.com/sdk/docs/install) をインストール後、`gcloud auth login` を実行してください。

---

## 方法B：GitHub Actions で動かす（GCP不要・完全無料）

1. GitHubで新しいリポジトリを作成し、このフォルダをアップロード
2. リポジトリの **Settings** → **Secrets and variables** → **Actions** に以下を登録：
   - `GEMINI_API_KEY`
   - `DISCORD_WEBHOOK_URL`
3. **Actions** タブ → **Daily Ireland News to Discord** → **Run workflow** でテスト実行

配信時刻の変更は `.github/workflows/daily_news.yml` の `cron`（UTC基準）を編集します。
