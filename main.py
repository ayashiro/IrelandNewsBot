import json
import os
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import requests
from google import genai
from google.genai import types

# アイルランドの主要ニュースソース（RSSフィード）
NEWS_SOURCES = [
    {
        "name": "RTÉ News",
        "url": "https://www.rte.ie/news/rss/news-headlines.xml",
        "site_url": "https://www.rte.ie/news/",
        "color": 0x169B62,  # アイルランドのグリーン
    },
    {
        "name": "The Irish Times",
        "url": "https://www.irishtimes.com/arc/outboundfeeds/digest-resolver/homepage-top/?from=0&size=15",
        "site_url": "https://www.irishtimes.com/",
        "color": 0x1A5276,  # ネイビー
    },
    {
        "name": "TheJournal.ie",
        "url": "https://www.thejournal.ie/feed/",
        "site_url": "https://www.thejournal.ie/",
        "color": 0xFF883E,  # アイルランドのオレンジ
    },
]

HEADLINES_PER_SOURCE = int(os.getenv("HEADLINES_PER_SOURCE", "5"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen")
USER_AGENT = "Mozilla/5.0 (compatible; IrelandNewsBot/1.0)"
DISPLAY_TZ = ZoneInfo(os.getenv("DISPLAY_TZ", "Europe/Dublin"))


def fetch_headlines(source: dict[str, Any], limit: int) -> list[dict[str, str]]:
    """指定されたRSSフィードから最新ヘッドラインを取得する"""
    try:
        response = requests.get(
            source["url"],
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[WARN] {source['name']} の取得に失敗しました: {exc}", file=sys.stderr)
        return []

    feed = feedparser.parse(response.content)
    items: list[dict[str, str]] = []

    for entry in feed.entries[:limit]:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if title and link:
            items.append({"title": title, "link": link})

    return items


def translate_headlines(
    api_key: str,
    articles_by_source: dict[str, list[dict[str, str]]],
) -> dict[str, str]:
    """Gemini APIを使ってすべてのヘッドラインを自然な日本語へ一括翻訳する"""
    indexed_titles: dict[str, str] = {}
    idx = 0
    for source_name, articles in articles_by_source.items():
        for article in articles:
            indexed_titles[str(idx)] = article["title"]
            article["id"] = str(idx)
            idx += 1

    if not indexed_titles:
        return {}

    prompt = (
        "以下のアイルランドの英語ニュース見出しを、日本のニュースサイトのような自然で簡潔な日本語の見出しに翻訳してください。\n"
        "出力は必ず入力と同じキー（文字列のID）を持つJSONオブジェクトのみを返してください。\n"
        "例: {\"0\": \"翻訳された見出し1\", \"1\": \"翻訳された見出し2\"}\n\n"
        f"入力:\n{json.dumps(indexed_titles, ensure_ascii=False, indent=2)}"
    )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    raw_text = (response.text or "").strip()
    try:
        translated = json.loads(raw_text)
        if isinstance(translated, dict):
            return {str(k): str(v).strip() for k, v in translated.items()}
    except json.JSONDecodeError as exc:
        print(f"[WARN] GeminiのJSON解析に失敗しました: {exc}\n{raw_text}", file=sys.stderr)

    return {}


def build_discord_payload(
    articles_by_source: dict[str, list[dict[str, str]]],
    translations: dict[str, str],
) -> dict[str, Any]:
    """Discord Webhook用のEmbedペイロードを作成する"""
    now_local = datetime.now(DISPLAY_TZ)
    date_str = now_local.strftime("%Y年%m月%d日")

    embeds: list[dict[str, Any]] = []
    for source in NEWS_SOURCES:
        source_name = source["name"]
        articles = articles_by_source.get(source_name, [])
        if not articles:
            continue

        lines: list[str] = []
        for i, article in enumerate(articles, start=1):
            ja_title = translations.get(article["id"], article["title"])
            # Markdownリンク内の角括弧をエスケープ
            safe_title = ja_title.replace("[", "［").replace("]", "］")
            lines.append(f"**{i}.** [{safe_title}]({article['link']})")

        embeds.append(
            {
                "title": f"📰 {source_name}",
                "url": source["site_url"],
                "description": "\n".join(lines),
                "color": source["color"],
            }
        )

    return {
        "username": "Ireland News Bot",
        "content": f"🇮🇪 **アイルランド最新ニュース ヘッドライン（{date_str}）**",
        "embeds": embeds,
    }


def post_to_discord(webhook_url: str, payload: dict[str, Any]) -> None:
    """Discord Webhookへ投稿する"""
    response = requests.post(webhook_url, json=payload, timeout=15)
    response.raise_for_status()


def main() -> None:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not gemini_api_key:
        print("[ERROR] 環境変数 GEMINI_API_KEY が設定されていません。", file=sys.stderr)
        sys.exit(1)
    if not discord_webhook_url:
        print("[ERROR] 環境変数 DISCORD_WEBHOOK_URL が設定されていません。", file=sys.stderr)
        sys.exit(1)

    articles_by_source: dict[str, list[dict[str, str]]] = {}
    total_articles = 0

    for source in NEWS_SOURCES:
        articles = fetch_headlines(source, HEADLINES_PER_SOURCE)
        articles_by_source[source["name"]] = articles
        total_articles += len(articles)
        print(f"[INFO] {source['name']}: {len(articles)} 件取得")

    if total_articles == 0:
        print("[ERROR] すべてのニュースソースから記事を取得できませんでした。", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] 合計 {total_articles} 件を Gemini ({GEMINI_MODEL}) で翻訳中...")
    translations = translate_headlines(gemini_api_key, articles_by_source)

    payload = build_discord_payload(articles_by_source, translations)
    post_to_discord(discord_webhook_url, payload)
    print("[INFO] Discordへの投稿が完了しました！")


if __name__ == "__main__":
    main()
