import os, json, time, requests
from datetime import datetime
from urllib.parse import urlencode

API_KEY = os.environ.get("NEWSAPI_KEY")
if not API_KEY:
    raise SystemExit("❌ NEWSAPI_KEY environment variable not set. Add it in GitHub Secrets.")

# Topics you want news for (add or remove as you like)
TOPICS = [
    "markets", "nifty 50", "sensex", "india economy",
    "gold price", "silver price", "copper price",
    "reliance", "tcs", "infosys", "hdfc", "icici", "sbin", "airtel"
]

BASE_URL = "https://newsapi.org/v2/everything"

def fetch_topic(query: str):
    """Fetch articles for a given query from NewsAPI"""
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "apiKey": API_KEY
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json().get("articles", [])

def normalize(article: dict, topic: str):
    """Simplify article JSON for frontend use"""
    return {
        "title": article.get("title"),
        "url": article.get("url"),
        "source": (article.get("source") or {}).get("name"),
        "publishedAt": article.get("publishedAt"),
        "topic": topic
    }

def parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return datetime.min

def main():
    seen_urls = set()
    results = []

    for topic in TOPICS:
        try:
            articles = fetch_topic(topic)
            for art in articles:
                url = art.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(normalize(art, topic))
            time.sleep(0.5)  # be nice to API
        except requests.HTTPError as e:
            print(f"⚠️ Error fetching {topic}: {e}")

    # Sort newest first
    results.sort(key=lambda a: parse_ts(a["publishedAt"] or ""), reverse=True)

    # Save to news.json at repo root
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✅ Wrote {len(results)} articles to news.json")

if __name__ == "__main__":
    main()
