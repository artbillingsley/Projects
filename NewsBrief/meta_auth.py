# meta_auth.py
"""
One-time OAuth2 flow to obtain a permanent Facebook Page token.
Covers Facebook Page + Instagram Business Account.
Run locally — opens a browser for Facebook Login.
"""
import http.server
import json
import urllib.parse
import webbrowser
import sys

import requests

# -- Fill in from your Meta Developer App --
APP_ID = os.environ.get("FB_APP_ID", "")
APP_SECRET = os.environ.get("FB_APP_SECRET", "")
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = ",".join([
    "pages_manage_posts",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_content_publish",
])

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
            self.wfile.write(b"<h1>Facebook authorization successful!</h1><p>You can close this tab.</p>")
        else:
            error = params.get("error_description", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>Error</h1><p>{error}</p>".encode())
            print(f"\nError: {error}", file=sys.stderr)
            sys.exit(1)

    def log_message(self, format, *args):
        pass


if not APP_ID or not APP_SECRET:
    print("ERROR: Set APP_ID and APP_SECRET before running.", file=sys.stderr)
    print("Get them from: https://developers.facebook.com/apps/", file=sys.stderr)
    sys.exit(1)

# Step 1: Open browser for authorization
auth_url = (
    f"https://www.facebook.com/v19.0/dialog/oauth"
    f"?client_id={APP_ID}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&scope={SCOPES}"
    f"&response_type=code"
)
print("Opening browser for Facebook authorization...")
webbrowser.open(auth_url)

server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
server.handle_request()

if not auth_code:
    print("No authorization code received.", file=sys.stderr)
    sys.exit(1)

# Step 2: Exchange code for short-lived user token
print("Exchanging code for access token...")
resp = requests.get(
    "https://graph.facebook.com/v19.0/oauth/access_token",
    params={
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    },
    timeout=30,
)
resp.raise_for_status()
short_token = resp.json()["access_token"]

# Step 3: Exchange for long-lived user token
print("Exchanging for long-lived token...")
resp = requests.get(
    "https://graph.facebook.com/v19.0/oauth/access_token",
    params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    },
    timeout=30,
)
resp.raise_for_status()
long_token = resp.json()["access_token"]

# Step 4: Get Page Access Token (never expires)
print("Fetching Page Access Token...")
resp = requests.get(
    "https://graph.facebook.com/v19.0/me/accounts",
    params={"access_token": long_token, "limit": 100},
    timeout=30,
)
resp.raise_for_status()
pages = resp.json().get("data", [])

# Also try to get COGNOSCERE LLC directly by known ID
COGNOSCERE_PAGE_ID = "343042179087985"
if not any(p["id"] == COGNOSCERE_PAGE_ID for p in pages):
    print(f"\nCOGNOSCERE LLC (ID: {COGNOSCERE_PAGE_ID}) not in /me/accounts.")
    print("Attempting direct page token request...")
    direct_resp = requests.get(
        f"https://graph.facebook.com/v19.0/{COGNOSCERE_PAGE_ID}",
        params={"fields": "name,access_token,id", "access_token": long_token},
        timeout=30,
    )
    if direct_resp.ok and "access_token" in direct_resp.json():
        direct_page = direct_resp.json()
        print(f"  Found via direct request: {direct_page.get('name', 'unknown')}")
        pages.append(direct_page)
    else:
        print(f"  Direct request failed: {direct_resp.json().get('error', {}).get('message', 'unknown')}")
        print("  This page may be managed through Facebook Business Manager.")
        print("  Try: https://business.facebook.com/settings/pages")

if not pages:
    # Debug: show what permissions the token has
    print("\nNo pages found. Checking token permissions...")
    debug_resp = requests.get(
        "https://graph.facebook.com/debug_token",
        params={"input_token": long_token, "access_token": long_token},
        timeout=15,
    )
    if debug_resp.ok:
        debug_data = debug_resp.json().get("data", {})
        scopes = debug_data.get("scopes", [])
        print(f"  Token scopes: {scopes}")
        print(f"  Token type: {debug_data.get('type', 'unknown')}")
        print(f"  User ID: {debug_data.get('user_id', 'unknown')}")
    print("\nThis means either:")
    print("  1. You didn't select any pages during the authorization screen")
    print("  2. The COGNOSCERE LLC page is managed by a different Facebook account")
    print("\nTo fix: go to https://www.facebook.com/settings/?tab=business_tools")
    print("Remove 'COGNOSCERE NewsBrief', then re-run this script.")
    print("When the browser opens, LOOK FOR the page selection step and CHECK the pages.")
    sys.exit(1)

print(f"\nFound {len(pages)} page(s):")
for i, page in enumerate(pages):
    print(f"  [{i}] {page['name']} (ID: {page['id']})")

# Print credentials for ALL pages
for page in pages:
    page_token = page["access_token"]
    page_id = page["id"]
    page_name = page["name"]

    # Fetch Instagram Business Account for each page
    resp = requests.get(
        f"https://graph.facebook.com/v19.0/{page_id}",
        params={"fields": "instagram_business_account", "access_token": page_token},
        timeout=30,
    )
    resp.raise_for_status()
    ig_data = resp.json().get("instagram_business_account", {})
    ig_account_id = ig_data.get("id", "")

    print(f"\n=== {page_name} (ID: {page_id}) ===")
    print(f"  FACEBOOK_ACCESS_TOKEN={page_token}")
    print(f"  FACEBOOK_PAGE_ID={page_id}")
    if ig_account_id:
        print(f"  INSTAGRAM_ACCOUNT_ID={ig_account_id}")
    else:
        print(f"  (no Instagram Business Account linked)")

# Let user select which page to use
if len(pages) == 1:
    selected = pages[0]
else:
    # Auto-select COGNOSCERE LLC if present, otherwise prompt
    cognoscere = [p for p in pages if p["id"] == "343042179087985"]
    if cognoscere:
        selected = cognoscere[0]
        print(f"\nAuto-selected: {selected['name']} (COGNOSCERE LLC)")
    else:
        choice = input(f"\nSelect page [0-{len(pages)-1}]: ").strip()
        selected = pages[int(choice)]
page_token = selected["access_token"]
page_id = selected["id"]
ig_data = {}
ig_account_id = ""

print(f"\n=== Meta OAuth Complete ===")
print(f"Page: {selected['name']} (ID: {page_id})")
print(f"Instagram Business Account: {ig_account_id}")
print(f"Page Token: {page_token[:40]}... (never expires)")
print(f"\nSet these on EC2:")
print(f"  FACEBOOK_ACCESS_TOKEN={page_token}")
print(f"  FACEBOOK_PAGE_ID={page_id}")
if ig_account_id:
    print(f"  INSTAGRAM_ACCOUNT_ID={ig_account_id}")
else:
    print("  WARNING: No Instagram Business Account linked to this page")
