"""One-time OAuth setup for Gmail and YouTube APIs.

Runs the browser-based consent flow and prints the refresh token
for the user to copy into .env.
"""

import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]
REDIRECT_URI = "http://localhost:8085"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


def get_env_or_exit(name: str) -> str:
    val = os.environ.get(name, "")
    if not val or val.startswith("your_"):
        print(f"Error: {name} not set in environment.", file=sys.stderr)
        print("Set it in .env and source it: export $(cat .env | xargs)", file=sys.stderr)
        sys.exit(1)
    return val


def main() -> None:
    client_id = get_env_or_exit("GOOGLE_CLIENT_ID")
    client_secret = get_env_or_exit("GOOGLE_CLIENT_SECRET")

    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in auth_params.items())}"

    authorization_code = None

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            nonlocal authorization_code
            query = parse_qs(urlparse(self.path).query)
            if "code" in query:
                authorization_code = query["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this tab.</p>")
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                error = query.get("error", ["unknown"])[0]
                self.wfile.write(f"<h1>Error: {error}</h1>".encode())

        def log_message(self, format: str, *args: object) -> None:
            pass

    print("Opening browser for Google OAuth consent...")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8085), Handler)
    print("Waiting for authorization callback on http://localhost:8085 ...")
    server.handle_request()

    if not authorization_code:
        print("Error: No authorization code received.", file=sys.stderr)
        sys.exit(1)

    print("Exchanging code for tokens...")
    resp = requests.post(
        TOKEN_URL,
        data={
            "code": authorization_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"Token exchange failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    tokens = resp.json()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("Error: No refresh token in response. Try revoking access and re-running.", file=sys.stderr)
        print(f"Response: {json.dumps(tokens, indent=2)}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("REFRESH TOKEN (copy this to .env as GOOGLE_REFRESH_TOKEN):")
    print("=" * 60)
    print(refresh_token)
    print("=" * 60)


if __name__ == "__main__":
    main()
