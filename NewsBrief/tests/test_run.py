# tests/test_run.py
from datetime import date

import pytest


def test_parse_args_defaults():
    from src.run import parse_args

    args = parse_args([])
    assert args.date is None
    assert args.preview is False
    assert args.dry_run is False
    assert args.force is False
    assert args.stage is None


def test_parse_args_with_date():
    from src.run import parse_args

    args = parse_args(["--date", "2026-06-10"])
    assert args.date == "2026-06-10"


def test_parse_args_with_flags():
    from src.run import parse_args

    args = parse_args(["--preview", "--force"])
    assert args.preview is True
    assert args.force is True


def test_resolve_run_date_uses_today_when_no_arg():
    from src.run import resolve_run_date

    result = resolve_run_date(None)
    assert result == date.today()


def test_resolve_run_date_parses_arg():
    from src.run import resolve_run_date

    result = resolve_run_date("2026-06-10")
    assert result == date(2026, 6, 10)
