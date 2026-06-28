# tests/test_post.py
from unittest.mock import MagicMock, patch
import pytest


def test_post_uploads_to_all_platforms():
    from src.stages.post import upload_all, UploadResult

    with patch("src.stages.post._upload_youtube_video", return_value={"platform_id": "yt1", "platform_url": "https://yt/1"}), \
         patch("src.stages.post._upload_youtube_short", return_value={"platform_id": "yt2", "platform_url": "https://yt/2"}), \
         patch("src.stages.post._upload_facebook_reel", return_value={"platform_id": "fb2", "platform_url": "https://fb/2"}), \
         patch("src.stages.post._upload_instagram_reel", return_value={"platform_id": "ig1", "platform_url": "https://ig/1"}), \
         patch("src.stages.post._upload_linkedin_video", return_value={"platform_id": "li1", "platform_url": "https://li/1"}):

        results = upload_all(
            output_dir="/tmp/output",
            spec={"date": "2026-06-10", "clips": [], "slots": []},
            config=MagicMock(),
        )

    assert len(results) == 5
    succeeded = [r for r in results if r.status == "completed"]
    assert len(succeeded) == 5


def test_post_isolates_platform_failures():
    from src.stages.post import upload_all

    with patch("src.stages.post._upload_youtube_video", return_value={"platform_id": "yt1", "platform_url": ""}), \
         patch("src.stages.post._upload_youtube_short", side_effect=Exception("YT Short failed")), \
         patch("src.stages.post._upload_facebook_reel", return_value={"platform_id": "fb2", "platform_url": ""}), \
         patch("src.stages.post._upload_instagram_reel", return_value={"platform_id": "ig1", "platform_url": ""}), \
         patch("src.stages.post._upload_linkedin_video", return_value={"platform_id": "li1", "platform_url": ""}):

        results = upload_all(
            output_dir="/tmp/output",
            spec={"date": "2026-06-10", "clips": [], "slots": []},
            config=MagicMock(),
        )

    failed = [r for r in results if r.status == "failed"]
    succeeded = [r for r in results if r.status == "completed"]
    assert len(failed) == 1
    assert len(succeeded) == 4
    assert failed[0].platform == "youtube_short"


def test_no_s3_dependency():
    """post.py should not import boto3 or reference S3."""
    import inspect
    import src.stages.post as post_module
    source = inspect.getsource(post_module)
    assert "boto3" not in source
    assert "s3_client" not in source
    assert "presigned" not in source
