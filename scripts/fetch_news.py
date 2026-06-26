"""Fetch news articles from Google News RSS via the gnews library.

No API key required. Free forever, no rate limits for daily use.

Outputs JSON to stdout:
    {"articles": [{"title", "source", "url", "description", "keywords", "published_at"}]}
"""

import json
import sys
from datetime import datetime

import yaml
from gnews import GNews

LOW_QUALITY_DOMAINS = {
    "yahoo.com", "msn.com", "newsbreak.com", "benzinga.com",
    "marketwatch.com", "seekingalpha.com", "investing.com",
    "cryptonews.net", "ambcrypto.com", "bitcoinist.com",
}


def load_config() -> dict:
    import os

    config_path = os.path.join(os.path.dirname(__file__), "..", "dna-config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def is_low_quality(url: str) -> bool:
    for domain in LOW_QUALITY_DOMAINS:
        if domain in url:
            return True
    return False


def parse_published_at(value) -> datetime:
    """Normalize a GNews published date to a datetime for sorting.

    GNews may return a datetime object or an RSS date string. Strings that
    cannot be parsed fall back to datetime.min so they sort at the end.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        formats = [
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return datetime.min


def fetch_keyword(client: GNews, keyword: str, per_keyword: int) -> list[dict]:
    try:
        results = client.get_news(keyword)
    except Exception as e:
        print(f"Google News error for '{keyword}': {e}", file=sys.stderr)
        return []

    articles = []
    for item in results:
        url = item.get("url", "")
        if is_low_quality(url):
            continue
        articles.append({
            "title": item.get("title", ""),
            "source": item.get("publisher", {}).get("title", ""),
            "url": url,
            "description": item.get("description", ""),
            "keywords": [keyword],
            "published_at": item.get("published date", ""),
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

    client = GNews(
        language="en",
        country="US",
        period="1d",
        max_results=per_keyword * 2,
    )

    all_articles: list[dict] = []
    seen_urls: dict[str, int] = {}

    for keyword in keywords:
        articles = fetch_keyword(client, keyword, per_keyword)

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

    # Sort by recency so the highest-priority (newest) articles appear first,
    # regardless of which keyword produced them.
    all_articles.sort(key=lambda a: parse_published_at(a.get("published_at")), reverse=True)
    all_articles = all_articles[:max_total]
    json.dump({"articles": all_articles}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
