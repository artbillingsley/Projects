# tests/test_retry.py
import pytest
from unittest.mock import MagicMock, patch


def test_retry_returns_on_first_success():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(return_value="ok")
    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert fn.call_count == 1


def test_retry_retries_on_failure_then_succeeds():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])
    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert fn.call_count == 3


def test_retry_raises_after_max_retries():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(side_effect=ValueError("always fails"))
    with pytest.raises(ValueError, match="always fails"):
        retry_with_backoff(fn, max_retries=2, base_delay=0.01)
    assert fn.call_count == 3  # initial + 2 retries


def test_retry_respects_specific_exception_types():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(side_effect=TypeError("wrong type"))
    with pytest.raises(TypeError):
        retry_with_backoff(fn, max_retries=3, base_delay=0.01, retry_on=(ValueError,))
    assert fn.call_count == 1  # no retry for TypeError
