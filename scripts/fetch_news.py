"""Fetch news articles from NewsAPI or GNews for configured keywords.

Outputs JSON to stdout:
    {"articles": [{"title", "source", "url", "description", "keywords", "published_at"}]}
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
import yaml

GST = timezone(timedelta(hours=4))
NEWSAPI_URL = "https://newsapi.org/v2/everything"
GNEWS_URL = "https://gnews.io/api/v4/search"

LOW_QUALITY_DOMAINS = {
    "yahoo.com", "msn.com", "newsbreak.com", "benzinga.com",
    "marketwatch.com", "seekingalpha.com", "investing.com",
    "cryptonews.net", "ambcrypto.com", "bitcoinist.com",
}


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "dna-config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_api_key(env_var: str) -> str:
    key = os.environ.get(env_var, "")
    if not key or key.startswith("your_"):
        return ""
    return key


def is_low_quality(url: str) -> bool:
    for domain in LOW_QUALITY_DOMAINS:
        if domain in url:
            return True
    return False


def fetch_newsapi(
    keyword: str, api_key: str, from_date: str, to_date: str, per_keyword: int,
) -> list[dict]:
    resp = requests.get(
        NEWSAPI_URL,
        params={
            "q": keyword,
            "from": from_date,
            "to": to_date,
            "sortBy": "relevancy",
            "pageSize": per_keyword * 2,
            "apiKey": api_key,
            "language": "en",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"NewsAPI error for '{keyword}': {resp.status_code} {resp.text}", file=sys.stderr)
        return []

    articles = []
    for art in resp.json().get("articles", []):
        url = art.get("url", "")
        if is_low_quality(url):
            continue
        articles.append({
            "title": art.get("title", ""),
            "source": art.get("source", {}).get("name", ""),
            "url": url,
            "description": art.get("description", ""),
            "keywords": [keyword],
            "published_at": art.get("publishedAt", ""),
        })
        if len(articles) >= per_keyword:
            break
    return articles


def fetch_gnews(
    keyword: str, api_key: str, from_date: str, to_date: str, per_keyword: int,
) -> list[dict]:
    resp = requests.get(
        GNEWS_URL,
        params={
            "q": keyword,
            "from": from_date,
            "to": to_date,
            "max": per_keyword * 2,
            "token": api_key,
            "lang": "en",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"GNews error for '{keyword}': {resp.status_code} {resp.text}", file=sys.stderr)
        return []

    articles = []
    for art in resp.json().get("articles", []):
        url = art.get("url", "")
        if is_low_quality(url):
            continue
        articles.append({
            "title": art.get("title", ""),
            "source": art.get("source", {}).get("name", ""),
            "url": url,
            "description": art.get("description", ""),
            "keywords": [keyword],
            "published_at": art.get("publishedAt", ""),
        })
        if len(articles) >= per_keyword:
            break
    return articles


def main() -> None:
    config = load_config()
    news_config = config["news"]

    keywords = news_config["keywords"]
    per_keyword = news_config["articles_per_keyword"]
    max_total = news_config["max_total_articles"]

    now = datetime.now(GST)
    from_date = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    to_date = now.strftime("%Y-%m-%dT%H:%M:%S")

    newsapi_key = get_api_key(news_config["api_key_env"])
    gnews_key = get_api_key(news_config.get("fallback_api_key_env", ""))

    if not newsapi_key and not gnews_key:
        print("Error: No news API key configured.", file=sys.stderr)
        sys.exit(1)

    use_newsapi = bool(newsapi_key)
    fetch_fn = fetch_newsapi if use_newsapi else fetch_gnews
    api_key = newsapi_key if use_newsapi else gnews_key

    all_articles: list[dict] = []
    seen_urls: dict[str, int] = {}

    for keyword in keywords:
        articles = fetch_fn(keyword, api_key, from_date, to_date, per_keyword)

        if not articles and not use_newsapi and gnews_key:
            articles = fetch_gnews(keyword, gnews_key, from_date, to_date, per_keyword)

        for article in articles:
            url = article["url"]
            if url in seen_urls:
                idx = seen_urls[url]
                existing_keywords = all_articles[idx]["keywords"]
                if keyword not in existing_keywords:
                    existing_keywords.append(keyword)
            else:
                seen_urls[url] = len(all_articles)
                all_articles.append(article)

    all_articles = all_articles[:max_total]
    json.dump({"articles": all_articles}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
