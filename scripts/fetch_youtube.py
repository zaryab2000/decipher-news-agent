"""Fetch unprocessed videos from a YouTube playlist.

Outputs JSON to stdout:
    {"videos": [{"video_id", "title", "channel", "duration", "url", "published_at"}]}
"""

import json
import os
import re
import sys
from datetime import timedelta, timezone

import requests
import yaml

GST = timezone(timedelta(hours=4))
TOKEN_URL = "https://oauth2.googleapis.com/token"
YT_API = "https://www.googleapis.com/youtube/v3"


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "dna-config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_state(state_file: str) -> dict:
    state_path = os.path.join(os.path.dirname(__file__), "..", state_file)
    if not os.path.exists(state_path):
        return {"processed_videos": [], "last_run": None}
    with open(state_path) as f:
        return json.load(f)


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


def parse_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M3S) to human-readable (1:02:03)."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return iso_duration

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def main() -> None:
    config = load_config()
    yt_config = config["youtube"]

    playlist_id = yt_config["playlist_id"]
    if playlist_id == "[PENDING]":
        print("Error: youtube.playlist_id not configured in dna-config.yaml", file=sys.stderr)
        sys.exit(1)

    max_videos = yt_config["max_videos"]
    state = load_state(yt_config["state_file"])
    processed_ids = {v["video_id"] for v in state["processed_videos"]}

    access_token = refresh_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    video_ids: list[str] = []
    page_token = None

    while True:
        params: dict = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(
            f"{YT_API}/playlistItems",
            params=params,
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"Playlist fetch failed: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)

        data = resp.json()
        for item in data.get("items", []):
            vid = item["snippet"]["resourceId"]["videoId"]
            if vid not in processed_ids:
                video_ids.append(vid)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    if not video_ids:
        json.dump({"videos": []}, sys.stdout, indent=2)
        print()
        return

    batch_size = 50
    videos: list[dict] = []

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i : i + batch_size]
        resp = requests.get(
            f"{YT_API}/videos",
            params={
                "part": "snippet,contentDetails",
                "id": ",".join(batch),
            },
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"Video details fetch failed: {resp.status_code}", file=sys.stderr)
            continue

        for item in resp.json().get("items", []):
            videos.append({
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "duration": parse_duration(
                    item["contentDetails"]["duration"]
                ),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "published_at": item["snippet"]["publishedAt"],
            })

    json.dump({"videos": videos}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
