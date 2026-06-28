# src/config.py
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    # Database
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str

    # Claude API
    anthropic_api_key: str

    # ElevenLabs (used in Plan B)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # YouTube (primary channel)
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    # YouTube 2 (@billinga channel)
    youtube2_client_id: str = ""
    youtube2_client_secret: str = ""
    youtube2_refresh_token: str = ""

    # YouTube 3
    youtube3_client_id: str = ""
    youtube3_client_secret: str = ""
    youtube3_refresh_token: str = ""

    # Facebook
    facebook_page_id: str = ""
    facebook_access_token: str = ""

    # Instagram
    instagram_account_id: str = ""

    # LinkedIn
    linkedin_access_token: str = ""
    linkedin_org_id: str = ""
    linkedin_member_id: str = ""

    # Bluesky
    bluesky_handle: str = ""
    bluesky_app_password: str = ""

    # Google Drive archive
    gdrive_client_id: str = ""
    gdrive_client_secret: str = ""
    gdrive_refresh_token: str = ""
    gdrive_folder_id: str = ""

    # Publish gate
    publish_mode: str = "preview"  # preview | gate | auto
    publish_platforms: str = ""  # comma-separated: youtube_video,youtube_short,facebook_video,...

    # Alerting
    sendgrid_api_key: str = ""
    alert_email_to: str = ""
    alert_email_from: str = ""

    @property
    def db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


_REQUIRED = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME", "ANTHROPIC_API_KEY"]


def load_config() -> Config:
    load_dotenv()
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")

    return Config(
        db_host=os.environ["DB_HOST"],
        db_port=int(os.environ["DB_PORT"]),
        db_user=os.environ["DB_USER"],
        db_password=os.environ["DB_PASSWORD"],
        db_name=os.environ["DB_NAME"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID", ""),
        youtube_client_id=os.environ.get("YOUTUBE_CLIENT_ID", ""),
        youtube_client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
        youtube_refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
        youtube2_client_id=os.environ.get("YOUTUBE2_CLIENT_ID", ""),
        youtube2_client_secret=os.environ.get("YOUTUBE2_CLIENT_SECRET", ""),
        youtube2_refresh_token=os.environ.get("YOUTUBE2_REFRESH_TOKEN", ""),
        youtube3_client_id=os.environ.get("YOUTUBE3_CLIENT_ID", ""),
        youtube3_client_secret=os.environ.get("YOUTUBE3_CLIENT_SECRET", ""),
        youtube3_refresh_token=os.environ.get("YOUTUBE3_REFRESH_TOKEN", ""),
        facebook_page_id=os.environ.get("FACEBOOK_PAGE_ID", ""),
        facebook_access_token=os.environ.get("FACEBOOK_ACCESS_TOKEN", ""),
        instagram_account_id=os.environ.get("INSTAGRAM_ACCOUNT_ID", ""),
        linkedin_access_token=os.environ.get("LINKEDIN_ACCESS_TOKEN", ""),
        linkedin_org_id=os.environ.get("LINKEDIN_ORG_ID", ""),
        linkedin_member_id=os.environ.get("LINKEDIN_MEMBER_ID", ""),
        bluesky_handle=os.environ.get("BLUESKY_HANDLE", ""),
        bluesky_app_password=os.environ.get("BLUESKY_APP_PASSWORD", ""),
        gdrive_client_id=os.environ.get("GDRIVE_CLIENT_ID", ""),
        gdrive_client_secret=os.environ.get("GDRIVE_CLIENT_SECRET", ""),
        gdrive_refresh_token=os.environ.get("GDRIVE_REFRESH_TOKEN", ""),
        gdrive_folder_id=os.environ.get("GDRIVE_FOLDER_ID", ""),
        publish_mode=os.environ.get("PUBLISH_MODE", "preview"),
        publish_platforms=os.environ.get("PUBLISH_PLATFORMS", ""),
        sendgrid_api_key=os.environ.get("SENDGRID_API_KEY", ""),
        alert_email_to=os.environ.get("ALERT_EMAIL_TO", ""),
        alert_email_from=os.environ.get("ALERT_EMAIL_FROM", ""),
    )
