"""
One-time OAuth2 flow to obtain a YouTube refresh token for @billinga channel.
Run locally — opens a browser for Google sign-in.
Sign in with: billinga-2420@pages.plusgoogle.com
"""
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_CONFIG = {
    "installed": {
        "client_id": "<YOUTUBE2_CLIENT_ID from .env>",
        "client_secret": "<YOUTUBE2_CLIENT_SECRET from .env>",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8080"],
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
credentials = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

print("\n=== YouTube OAuth Complete (@billinga) ===")
print(f"Refresh Token: {credentials.refresh_token}")
print(f"\nSet this on EC2:")
print(f"  YOUTUBE2_CLIENT_ID=<YOUTUBE2_CLIENT_ID from .env>")
print(f"  YOUTUBE2_CLIENT_SECRET=<YOUTUBE2_CLIENT_SECRET from .env>")
print(f"  YOUTUBE2_REFRESH_TOKEN={credentials.refresh_token}")
