"""Stage 2b: FORMAT — Convert canonical numeric values to spoken forms for TTS."""

import re


# ---------------------------------------------------------------------------
# Core number-to-words helper
# ---------------------------------------------------------------------------

_ONES = [
    "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]

_TENS = [
    "", "", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety",
]


def _int_to_words(n: int) -> str:
    """Convert a non-negative integer to its English spoken form."""
    if n < 0:
        return "negative " + _int_to_words(-n)
    if n == 0:
        return "zero"
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens = _TENS[n // 10]
        ones = _ONES[n % 10]
        return tens + (" " + ones if ones else "")
    if n < 1_000:
        hundreds = _ONES[n // 100] + " hundred"
        remainder = n % 100
        return hundreds + (" " + _int_to_words(remainder) if remainder else "")
    if n < 1_000_000:
        thousands = _int_to_words(n // 1_000) + " thousand"
        remainder = n % 1_000
        return thousands + (" " + _int_to_words(remainder) if remainder else "")
    if n < 1_000_000_000:
        millions = _int_to_words(n // 1_000_000) + " million"
        remainder = n % 1_000_000
        return millions + (" " + _int_to_words(remainder) if remainder else "")
    billions = _int_to_words(n // 1_000_000_000) + " billion"
    remainder = n % 1_000_000_000
    return billions + (" " + _int_to_words(remainder) if remainder else "")


def _parse_int(s: str) -> int:
    """Parse a string of digits (with optional commas) to int."""
    return int(s.replace(",", ""))


# ---------------------------------------------------------------------------
# Individual substitution helpers
# ---------------------------------------------------------------------------

def _replace_dollar_units(text: str) -> str:
    """Replace $X billion/million/trillion with spoken form.

    If followed by another word (adjective use), use singular 'dollar'.
    If at end or followed by punctuation/whitespace-then-end, use 'dollars'.

    Examples:
        $70 billion immigration bill  -> seventy billion dollar immigration bill
        $850 billion                  -> eight hundred fifty billion dollars
    """
    # Pattern: optional comma-digits before decimal, with scale word
    pattern = re.compile(
        r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s+'
        r'(billion|million|trillion)'
        r'(?=(\s+\w+)|($|[^a-zA-Z0-9]))',
        re.IGNORECASE,
    )

    def _repl(m: re.Match) -> str:
        raw_num = m.group(1).replace(",", "")
        scale = m.group(2).lower()
        following_word = m.group(3)  # " word" if present, else None

        # Convert the number part
        if "." in raw_num:
            integer_part = int(raw_num.split(".")[0])
            words = _int_to_words(integer_part)
        else:
            words = _int_to_words(int(raw_num))

        if following_word:
            # Adjective position — singular "dollar"
            return f"{words} {scale} dollar"
        else:
            # Standalone — plural "dollars"
            return f"{words} {scale} dollars"

    return pattern.sub(_repl, text)


def _replace_dollar_price(text: str) -> str:
    """Replace $X.XX price amounts with spoken form (no 'dollars' suffix).

    Example: $4.16 -> four sixteen
    """
    pattern = re.compile(r'\$([0-9]+)\.([0-9]{2})\b')

    def _repl(m: re.Match) -> str:
        dollars = int(m.group(1))
        cents = int(m.group(2))
        return f"{_int_to_words(dollars)} {_int_to_words(cents)}"

    return pattern.sub(_repl, text)


def _vote_number_to_words(n: int) -> str:
    """Speak a vote-tally number the way a news anchor would.

    3-digit numbers are spoken as two parts: the leading digit then the
    trailing two digits (e.g. 214 -> "two fourteen", 212 -> "two twelve").
    2-digit numbers use standard words (e.g. 98 -> "ninety eight").
    """
    if n >= 100:
        lead = _int_to_words(n // 100)
        tail = _int_to_words(n % 100)
        return f"{lead} {tail}"
    return _int_to_words(n)


def _replace_vote_tally(text: str) -> str:
    """Replace NNN-NNN vote tallies with 'N to N'.

    Example: 214-212 -> two fourteen to two twelve
    We target 2-3 digit hyphenated pairs typical of vote counts.
    """
    pattern = re.compile(r'\b([0-9]{2,3})-([0-9]{2,3})\b')

    def _repl(m: re.Match) -> str:
        a = _vote_number_to_words(int(m.group(1)))
        b = _vote_number_to_words(int(m.group(2)))
        return f"{a} to {b}"

    return pattern.sub(_repl, text)


def _replace_decimal_percent(text: str) -> str:
    """Replace N.N percent with 'N point N percent'.

    Example: 3.8 percent -> three point eight percent
    """
    pattern = re.compile(r'\b([0-9]+)\.([0-9]+)\s+percent\b', re.IGNORECASE)

    def _repl(m: re.Match) -> str:
        integer_words = _int_to_words(int(m.group(1)))
        # Each digit after decimal spoken individually
        decimal_digits = m.group(2)
        decimal_words = " ".join(_int_to_words(int(d)) for d in decimal_digits)
        return f"{integer_words} point {decimal_words} percent"

    return pattern.sub(_repl, text)


_YEAR_RE = re.compile(r'\b(1[0-9]{3}|20[0-9]{2})\b')


def _is_year(n: int) -> bool:
    return 1900 <= n <= 2099


def _replace_plain_numbers(text: str) -> str:
    """Replace plain integers (with optional commas) with spoken form.

    Years 1900-2099 are left as digits.
    """
    # Match numbers with optional comma-grouping, not preceded or followed by
    # characters that would make them part of something else (e.g., decimals,
    # already-converted dollar signs handled above).
    pattern = re.compile(r'\b([0-9]{1,3}(?:,[0-9]{3})*)\b')

    def _repl(m: re.Match) -> str:
        raw = m.group(1)
        n = int(raw.replace(",", ""))
        if _is_year(n):
            return raw  # leave as-is
        return _int_to_words(n)

    return pattern.sub(_repl, text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def format_for_speech(text: str) -> str:
    """Convert numeric values in *text* to TTS-friendly spoken forms.

    Substitutions are applied most-specific first:
    1. $X billion/million/trillion  -> "{words} {scale} dollar[s]"
    2. $X.XX price                  -> "{dollars} {cents}" (no suffix)
    3. NNN-NNN vote tallies         -> "{a} to {b}"
    4. N.N percent                  -> "{N} point {N} percent"
    5. Plain integers (with commas) -> spoken words  (years 1900-2099 skipped)
    """
    text = _replace_dollar_units(text)
    text = _replace_dollar_price(text)
    text = _replace_vote_tally(text)
    text = _replace_decimal_percent(text)
    text = _replace_plain_numbers(text)
    return text
