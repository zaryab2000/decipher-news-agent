"""Fetch newsletter emails from Gmail using OAuth.

Outputs JSON to stdout:
    {"articles": [{"subject", "from", "date", "body_text", "body_html"}]}
"""

import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
import yaml

GST = timezone(timedelta(hours=4))
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "dna-config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_env_or_exit(name: str) -> str:
    val = os.environ.get(name, "")
    if not val or val.startswith("your_"):
        print(f"Error: {name} not set in environment.", file=sys.stderr)
        sys.exit(1)
    return val


def refresh_access_token() -> str:
    client_id = get_env_or_exit("GOOGLE_CLIENT_ID")
    client_secret = get_env_or_exit("GOOGLE_CLIENT_SECRET")
    refresh_token = get_env_or_exit("GOOGLE_REFRESH_TOKEN")

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Token refresh failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    return resp.json()["access_token"]


def get_header_value(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def extract_body(payload: dict) -> tuple[str, str]:
    """Extract text/plain and text/html body from message payload."""
    text_body = ""
    html_body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data", "")
            if mime == "text/plain" and data:
                text_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            elif mime == "text/html" and data:
                html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if "parts" in part:
                sub_text, sub_html = extract_body(part)
                if not text_body:
                    text_body = sub_text
                if not html_body:
                    html_body = sub_html
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            mime = payload.get("mimeType", "")
            if mime == "text/plain":
                text_body = decoded
            elif mime == "text/html":
                html_body = decoded

    return text_body, html_body


def load_state(config: dict) -> dict:
    """Load dna-state.json, returning empty dict if missing or invalid."""
    state_file = config.get("youtube", {}).get("state_file", "dna-state.json")
    state_path = os.path.join(os.path.dirname(__file__), "..", state_file)
    try:
        with open(state_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def build_gmail_query(label: str, state: dict, lookback_hours: int) -> str:
    """Build Gmail search query using last run timestamp or lookback fallback.

    Args:
        label: Gmail label to filter by.
        state: Parsed dna-state.json contents.
        lookback_hours: Fallback lookback window for first run.

    Returns:
        Gmail search query string.
    """
    now = datetime.now(GST)
    gmail_last_run = state.get("gmail_last_run")

    if gmail_last_run:
        last_run_dt = datetime.fromisoformat(gmail_last_run)
        after_epoch = int(last_run_dt.timestamp())
        after_filter = f"after:{after_epoch}"
    else:
        after_date = (now - timedelta(hours=lookback_hours)).strftime("%Y/%m/%d")
        after_filter = f"after:{after_date}"

    before_date = (now + timedelta(days=1)).strftime("%Y/%m/%d")
    return f"label:{label} {after_filter} before:{before_date}"


def main() -> None:
    config = load_config()
    gmail_config = config["gmail"]
    label = gmail_config["label"]
    lookback = gmail_config["lookback_hours"]

    state = load_state(config)
    access_token = refresh_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    query = build_gmail_query(label, state, lookback)

    resp = requests.get(
        f"{GMAIL_API}/messages",
        params={"q": query, "maxResults": 50},
        headers=headers,
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Gmail search failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    messages = resp.json().get("messages", [])
    if not messages:
        json.dump({"articles": []}, sys.stdout, indent=2)
        print()
        return

    articles = []
    for msg_ref in messages:
        msg_resp = requests.get(
            f"{GMAIL_API}/messages/{msg_ref['id']}",
            params={"format": "full"},
            headers=headers,
            timeout=15,
        )
        if msg_resp.status_code != 200:
            print(f"Failed to fetch message {msg_ref['id']}", file=sys.stderr)
            continue

        msg = msg_resp.json()
        msg_headers = msg.get("payload", {}).get("headers", [])
        text_body, html_body = extract_body(msg.get("payload", {}))

        articles.append({
            "subject": get_header_value(msg_headers, "Subject"),
            "from": get_header_value(msg_headers, "From"),
            "date": get_header_value(msg_headers, "Date"),
            "body_text": text_body,
            "body_html": html_body,
        })

    json.dump({"articles": articles}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
