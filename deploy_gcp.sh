#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# GCP (Cloud Run Jobs + Cloud Scheduler + Secret Manager)
# 自動デプロイスクリプト（Cloud Shell / Linux / macOS 用）
# ============================================================

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-asia-northeast1}"          # 東京リージョン（アイルランドなら europe-west1 等も可）
JOB_NAME="${JOB_NAME:-ireland-news-bot}"
SCHEDULER_NAME="${SCHEDULER_NAME:-ireland-news-daily}"
SCHEDULE="${SCHEDULE:-0 8 * * *}"            # 毎日 08:00
TIME_ZONE="${TIME_ZONE:-Asia/Tokyo}"         # 日本時間（アイルランド時間なら Europe/Dublin）
HEADLINES_PER_SOURCE="${HEADLINES_PER_SOURCE:-5}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "[ERROR] PROJECT_ID が未設定です。例: PROJECT_ID=your-gcp-project-id ./deploy_gcp.sh"
  exit 1
fi

if [[ -z "${GEMINI_API_KEY:-}" || -z "${DISCORD_WEBHOOK_URL:-}" ]]; then
  echo "[ERROR] 環境変数 GEMINI_API_KEY と DISCORD_WEBHOOK_URL を設定してから実行してください。"
  echo "例:"
  echo "  export GEMINI_API_KEY='...'"
  echo "  export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/...'"
  echo "  ./deploy_gcp.sh"
  exit 1
fi

echo "==> プロジェクトを設定: ${PROJECT_ID} (リージョン: ${REGION})"
gcloud config set project "${PROJECT_ID}"

echo "==> 必要なAPIを有効化中..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com

upsert_secret() {
  local secret_name="$1"
  local secret_value="$2"
  if gcloud secrets describe "${secret_name}" >/dev/null 2>&1; then
    printf "%s" "${secret_value}" | gcloud secrets versions add "${secret_name}" --data-file=-
  else
    printf "%s" "${secret_value}" | gcloud secrets create "${secret_name}" --replication-policy="automatic" --data-file=-
  fi
}

echo "==> Secret Manager にシークレットを登録中..."
upsert_secret "ireland-news-gemini-api-key" "${GEMINI_API_KEY}"
upsert_secret "ireland-news-discord-webhook" "${DISCORD_WEBHOOK_URL}"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "==> サービスアカウント (${RUNTIME_SA}) に権限を付与中..."
for secret in ireland-news-gemini-api-key ireland-news-discord-webhook; do
  gcloud secrets add-iam-policy-binding "${secret}" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet >/dev/null
done

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/run.invoker" \
  --quiet >/dev/null

echo "==> Cloud Run Job (${JOB_NAME}) をビルド＆デプロイ中..."
gcloud run jobs deploy "${JOB_NAME}" \
  --source . \
  --region "${REGION}" \
  --set-env-vars "HEADLINES_PER_SOURCE=${HEADLINES_PER_SOURCE}" \
  --set-secrets "GEMINI_API_KEY=ireland-news-gemini-api-key:latest,DISCORD_WEBHOOK_URL=ireland-news-discord-webhook:latest" \
  --max-retries 1 \
  --task-timeout 120s

JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"

echo "==> Cloud Scheduler (${SCHEDULER_NAME}: ${SCHEDULE} ${TIME_ZONE}) を設定中..."
if gcloud scheduler jobs describe "${SCHEDULER_NAME}" --location "${REGION}" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "${SCHEDULER_NAME}" \
    --location "${REGION}" \
    --schedule "${SCHEDULE}" \
    --time-zone "${TIME_ZONE}" \
    --uri "${JOB_URI}" \
    --http-method POST \
    --oauth-service-account-email "${RUNTIME_SA}"
else
  gcloud scheduler jobs create http "${SCHEDULER_NAME}" \
    --location "${REGION}" \
    --schedule "${SCHEDULE}" \
    --time-zone "${TIME_ZONE}" \
    --uri "${JOB_URI}" \
    --http-method POST \
    --oauth-service-account-email "${RUNTIME_SA}"
fi

echo ""
echo "✅ デプロイ完了！すぐにテスト実行するには以下を実行してください:"
echo "   gcloud run jobs execute ${JOB_NAME} --region ${REGION} --wait"
