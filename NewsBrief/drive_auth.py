"""
One-time OAuth2 flow to obtain a Google Drive refresh token.
Run locally — opens a browser for Google sign-in.
Uses the same GCP project as YouTube.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_CONFIG = {
    "installed": {
        "client_id": "<GDRIVE_CLIENT_ID from .env>",
        "client_secret": "<GDRIVE_CLIENT_SECRET from .env>",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8080"],
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]

flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
credentials = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

print("\n=== Google Drive OAuth Complete ===")
print(f"Refresh Token: {credentials.refresh_token}")
print(f"\nSet this on EC2:")
print(f"  GDRIVE_REFRESH_TOKEN={credentials.refresh_token}")
