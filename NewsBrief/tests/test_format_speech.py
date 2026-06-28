# tests/test_format_speech.py
import pytest


def test_format_dollar_amount():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("Gas sits at $4.16 a gallon.") == "Gas sits at four sixteen a gallon."


def test_format_billion_dollar_amount():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("a $70 billion immigration bill") == "a seventy billion dollar immigration bill"


def test_format_large_billion():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("above $850 billion") == "above eight hundred fifty billion dollars"


def test_format_percentage():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("inflation hit 3.8 percent") == "inflation hit three point eight percent"


def test_format_vote_tally():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("a 214-212 vote") == "a two fourteen to two twelve vote"


def test_format_year():
    from src.stages.format_speech import format_for_speech

    # Years should be left as digits — ElevenLabs handles them well
    assert format_for_speech("funded through 2029") == "funded through 2029"


def test_format_plain_number():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("roughly 244,600 people killed") == "roughly two hundred forty four thousand six hundred people killed"


def test_format_leaves_non_numeric_text_unchanged():
    from src.stages.format_speech import format_for_speech

    text = "Iran shot down a U.S. Army Apache near the Strait of Hormuz."
    assert format_for_speech(text) == text


def test_format_one_fifth():
    from src.stages.format_speech import format_for_speech

    # Fractions like "a fifth" are already words — no change
    assert format_for_speech("carries one fifth of the world's oil") == "carries one fifth of the world's oil"
