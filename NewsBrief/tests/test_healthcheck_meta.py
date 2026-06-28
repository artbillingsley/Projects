from unittest.mock import patch, MagicMock
from src.healthcheck import check_meta_token


@patch("src.healthcheck.requests")
def test_valid_token_returns_true(mock_requests):
    resp = MagicMock()
    resp.json.return_value = {
        "data": {"is_valid": True, "expires_at": 0, "app_id": "123"}
    }
    resp.raise_for_status = MagicMock()
    mock_requests.get.return_value = resp
    assert check_meta_token("valid_token") is True


@patch("src.healthcheck.requests")
def test_invalid_token_returns_false(mock_requests):
    resp = MagicMock()
    resp.json.return_value = {
        "data": {"is_valid": False, "error": {"message": "expired"}}
    }
    resp.raise_for_status = MagicMock()
    mock_requests.get.return_value = resp
    assert check_meta_token("expired_token") is False


@patch("src.healthcheck.requests")
def test_network_error_returns_false(mock_requests):
    mock_requests.get.side_effect = Exception("Connection refused")
    assert check_meta_token("any_token") is False
