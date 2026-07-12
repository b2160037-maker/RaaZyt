"""get_token.py -- ONE-TIME local YouTube OAuth to produce token.json.

Run this ONCE on your own computer (not in Actions):

    pip install google-auth-oauthlib google-api-python-client
    # put your downloaded OAuth desktop client as client_secret.json next to this file
    python get_token.py

It opens a browser, you approve your channel, and it writes token.json.
Then paste:
    client_secret.json  -> GitHub secret  YT_CLIENT_SECRET_JSON
    token.json          -> GitHub secret  YT_TOKEN_JSON
From then on Actions refreshes the token automatically -- no re-login.
"""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

HERE = Path(__file__).parent
CLIENT = HERE / "client_secret.json"
TOKEN = HERE / "token.json"


def main():
    if not CLIENT.exists():
        raise SystemExit(
            "client_secret.json not found. Download it from Google Cloud Console "
            "(OAuth client, type = Desktop) and place it next to get_token.py."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    print("\nSaved " + str(TOKEN))
    print("Now paste client_secret.json -> YT_CLIENT_SECRET_JSON")
    print("and       token.json         -> YT_TOKEN_JSON  (GitHub Secrets).")


if __name__ == "__main__":
    main()
