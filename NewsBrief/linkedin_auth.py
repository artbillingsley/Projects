"""
One-time OAuth2 flow to obtain a LinkedIn access token + refresh token.
Run locally — opens a browser for LinkedIn sign-in.
"""
import http.server
import urllib.parse
import webbrowser
import requests
import sys

CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "openid profile w_member_social"

auth_code = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>LinkedIn authorization successful!</h1><p>You can close this tab.</p>")
        else:
            error = params.get("error", ["unknown"])[0]
            desc = params.get("error_description", [""])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>Error: {error}</h1><p>{desc}</p>".encode())
            print(f"\nError: {error} — {desc}", file=sys.stderr)
            sys.exit(1)

    def log_message(self, format, *args):
        pass  # silence request logs


# Step 1: Open browser for authorization
auth_url = (
    f"https://www.linkedin.com/oauth/v2/authorization"
    f"?response_type=code"
    f"&client_id={CLIENT_ID}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&scope={urllib.parse.quote(SCOPES)}"
)

print("Opening browser for LinkedIn authorization...")
webbrowser.open(auth_url)

# Step 2: Wait for callback
server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
server.handle_request()

if not auth_code:
    print("No authorization code received.", file=sys.stderr)
    sys.exit(1)

# Step 3: Exchange code for tokens
print("Exchanging authorization code for tokens...")
token_resp = requests.post(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    },
    timeout=30,
)
token_resp.raise_for_status()
token_data = token_resp.json()

access_token = token_data["access_token"]
expires_in = token_data.get("expires_in", "unknown")
refresh_token = token_data.get("refresh_token", "")
refresh_expires = token_data.get("refresh_token_expires_in", "unknown")

print(f"\n=== LinkedIn OAuth Complete ===")
print(f"Access Token: {access_token[:40]}...  ({expires_in}s / {round(int(expires_in)/86400)}d)")
if refresh_token:
    print(f"Refresh Token: {refresh_token[:40]}...  ({refresh_expires}s / {round(int(refresh_expires)/86400)}d)")
else:
    print("Refresh Token: (none — app may not have refresh token permission)")

print(f"\nSet these on EC2:")
print(f"  LINKEDIN_ACCESS_TOKEN={access_token}")
if refresh_token:
    print(f"  LINKEDIN_REFRESH_TOKEN={refresh_token}")
print(f"  LINKEDIN_ORG_ID=37801182")
