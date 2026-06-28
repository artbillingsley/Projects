from unittest.mock import patch, MagicMock, mock_open
import pytest

from src.lib.platforms.instagram import upload_reel


@patch("src.lib.platforms.instagram.requests")
def test_upload_reel_creates_container(mock_requests):
    create_resp = MagicMock()
    create_resp.json.return_value = {"id": "container_123"}
    create_resp.raise_for_status = MagicMock()

    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()

    poll_resp = MagicMock()
    poll_resp.json.return_value = {"status_code": "FINISHED"}
    poll_resp.raise_for_status = MagicMock()

    publish_resp = MagicMock()
    publish_resp.json.return_value = {"id": "media_456"}
    publish_resp.raise_for_status = MagicMock()

    mock_requests.post.side_effect = [create_resp, publish_resp]
    mock_requests.put.return_value = put_resp
    mock_requests.get.return_value = poll_resp

    with patch("builtins.open", mock_open(read_data=b"fake_video_bytes")):
        with patch("os.path.getsize", return_value=1024):
            result = upload_reel(
                ig_account_id="ig_123",
                access_token="token_abc",
                file_path="/tmp/video.mp4",
                caption="Test caption",
            )

    assert result["platform_id"] == "media_456"
    assert mock_requests.post.call_count == 2
    assert mock_requests.put.called


@patch("src.lib.platforms.instagram.requests")
def test_upload_reel_raises_on_error_status(mock_requests):
    create_resp = MagicMock()
    create_resp.json.return_value = {"id": "container_123"}
    create_resp.raise_for_status = MagicMock()

    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()

    poll_resp = MagicMock()
    poll_resp.json.return_value = {"status_code": "ERROR"}
    poll_resp.raise_for_status = MagicMock()

    mock_requests.post.return_value = create_resp
    mock_requests.put.return_value = put_resp
    mock_requests.get.return_value = poll_resp

    with patch("builtins.open", mock_open(read_data=b"fake")):
        with patch("os.path.getsize", return_value=512):
            with pytest.raises(RuntimeError, match="failed processing"):
                upload_reel(
                    ig_account_id="ig_123",
                    access_token="token_abc",
                    file_path="/tmp/video.mp4",
                    caption="Test",
                )


@patch("src.lib.platforms.instagram.requests")
def test_upload_reel_uses_file_path_not_url(mock_requests):
    create_resp = MagicMock()
    create_resp.json.return_value = {"id": "c1"}
    create_resp.raise_for_status = MagicMock()
    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()
    poll_resp = MagicMock()
    poll_resp.json.return_value = {"status_code": "FINISHED"}
    poll_resp.raise_for_status = MagicMock()
    pub_resp = MagicMock()
    pub_resp.json.return_value = {"id": "m1"}
    pub_resp.raise_for_status = MagicMock()

    mock_requests.post.side_effect = [create_resp, pub_resp]
    mock_requests.put.return_value = put_resp
    mock_requests.get.return_value = poll_resp

    with patch("builtins.open", mock_open(read_data=b"data")):
        with patch("os.path.getsize", return_value=256):
            result = upload_reel(
                ig_account_id="ig_123",
                access_token="tok",
                file_path="/tmp/test.mp4",
                caption="cap",
            )

    assert result["platform_id"] == "m1"
    assert mock_requests.put.called
