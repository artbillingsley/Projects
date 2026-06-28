# tests/test_s3.py
from unittest.mock import MagicMock
import pytest


def test_upload_and_get_presigned_url():
    from src.lib.platforms.s3 import upload_for_presigned_url

    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://bucket.s3.amazonaws.com/clip.mp4?sig=abc"

    result = upload_for_presigned_url(
        s3_client=mock_s3,
        bucket="newsbrief-temp",
        file_path="/tmp/clip.mp4",
        object_key="2026-06-10/clip-C3.mp4",
        expires_in=900,
    )

    assert "s3.amazonaws.com" in result
    mock_s3.upload_file.assert_called_once_with(
        "/tmp/clip.mp4", "newsbrief-temp", "2026-06-10/clip-C3.mp4"
    )
    mock_s3.generate_presigned_url.assert_called_once()


def test_presigned_url_uses_correct_expiry():
    from src.lib.platforms.s3 import upload_for_presigned_url

    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://example.com/signed"

    upload_for_presigned_url(
        s3_client=mock_s3,
        bucket="b",
        file_path="/tmp/f.mp4",
        object_key="k",
        expires_in=600,
    )

    call_kwargs = mock_s3.generate_presigned_url.call_args.kwargs
    assert call_kwargs["ExpiresIn"] == 600
