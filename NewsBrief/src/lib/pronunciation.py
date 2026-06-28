"""Pronunciation engine: loads SSML dictionary from YAML, injects phoneme tags,
detects unknown proper nouns, and implements the proper-noun gate (R8)."""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Set


# ---------------------------------------------------------------------------
# Common English words and well-known geopolitical terms that appear
# capitalised in news text but are NOT proper nouns requiring pronunciation
# review.
# ---------------------------------------------------------------------------
_COMMON_WORDS: Set[str] = {
    # Standard sentence-starters / common capitalised words
    "The", "This", "That", "Here", "And", "But", "Not",
    "One", "Two", "Three", "Four", "Five", "Now",
    # Geopolitical / institutional terms common in news
    "Iran", "Army", "Central", "Command", "House", "President",
    "Congress", "Senate", "Republican", "Democratic", "American",
    "United", "States", "Wall", "Street", "Journal", "New",
    "York", "Times", "Washington", "Post",
    # Common geographic terms that appear capitalised in news
    "Strait", "Gulf", "Bay", "River", "Lake", "Sea", "Ocean",
    "North", "South", "East", "West", "Middle", "Eastern",
    "City", "County", "District", "Island", "Islands",
    # Common institutional / role nouns
    "Minister", "Secretary", "General", "Director", "Chief",
    "White", "National", "Federal", "State", "Supreme", "Court",
    # Possessive / contraction artefacts handled separately, but include
    # plain forms for safety
    "U.S",  # U.S. stripped of trailing dot
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PronunciationDict:
    """Holds all pronunciation data loaded from YAML."""

    proper_nouns: Dict[str, str] = field(default_factory=dict)
    speak_as_word: Set[str] = field(default_factory=set)
    spell_out: Set[str] = field(default_factory=set)

    @property
    def all_known_words(self) -> Set[str]:
        """Case-insensitive union of all known terms (upper-cased for lookup)."""
        known: Set[str] = set()
        known.update(w.upper() for w in self.proper_nouns)
        known.update(w.upper() for w in self.speak_as_word)
        known.update(w.upper() for w in self.spell_out)
        return known


@dataclass
class GateResult:
    """Result of the proper-noun gate check."""

    requires_review: bool
    unknown_words: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_dictionary(yaml_path: str) -> PronunciationDict:
    """Load a PronunciationDict from a YAML file.

    Expected YAML structure::

        proper_nouns:
          Hormuz: '<phoneme ...>Hormuz</phoneme>'
        acronyms:
          speak_as_word:
            - NATO
          spell_out:
            - ICE
    """
    with open(yaml_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    proper_nouns: Dict[str, str] = data.get("proper_nouns") or {}
    acronyms = data.get("acronyms") or {}
    speak_as_word: Set[str] = set(acronyms.get("speak_as_word") or [])
    spell_out: Set[str] = set(acronyms.get("spell_out") or [])

    return PronunciationDict(
        proper_nouns=proper_nouns,
        speak_as_word=speak_as_word,
        spell_out=spell_out,
    )


def inject_ssml(text: str, dictionary: PronunciationDict) -> str:
    """Replace known proper nouns in *text* with their SSML phoneme tags.

    Uses whole-word, case-insensitive regex matching so partial matches are
    avoided.  Only ``proper_nouns`` entries carry explicit SSML; acronyms are
    left as-is (ElevenLabs handles them via other mechanisms).
    """
    result = text
    for word, ssml_tag in dictionary.proper_nouns.items():
        # \b gives word-boundary; re.IGNORECASE so "hormuz" matches "Hormuz"
        pattern = r"\b" + re.escape(word) + r"\b"
        result = re.sub(pattern, ssml_tag, result, flags=re.IGNORECASE)
    return result


def _extract_capitalized_words(text: str) -> List[str]:
    """Return words from *text* that look like proper nouns.

    A word qualifies when it starts with an uppercase letter (or is an
    all-caps acronym) and is not a run-of-the-mill sentence-starter captured
    in *_COMMON_WORDS*.

    Possessive suffixes ("'s") are stripped before the word is returned.
    """
    # Tokenise on whitespace, strip surrounding punctuation
    tokens = re.findall(r"[A-Za-z][A-Za-z'.-]*", text)
    candidates: List[str] = []
    for token in tokens:
        # Strip trailing possessive / punctuation artefacts
        clean = re.sub(r"'s$", "", token)   # Netanyahu's -> Netanyahu
        clean = clean.strip(".,!?;:")

        if not clean:
            continue

        # Must start uppercase to be a potential proper noun
        if not (clean[0].isupper() or clean.isupper()):
            continue

        # Skip common words
        if clean in _COMMON_WORDS:
            continue

        candidates.append(clean)

    return candidates


def find_unknown_proper_nouns(
    candidate_words: List[str],
    dictionary: PronunciationDict,
) -> List[str]:
    """Return the subset of *candidate_words* not present in *dictionary*.

    Comparison is case-insensitive.
    """
    known = dictionary.all_known_words
    unknown: List[str] = []
    for word in candidate_words:
        if word.upper() not in known:
            unknown.append(word)
    return unknown


def check_proper_noun_gate(
    hook_text: str,
    lead_text: str,
    dictionary: PronunciationDict,
) -> GateResult:
    """Implement the proper-noun gate (R8).

    Extracts capitalised words from the combined HOOK + LEAD text, filters
    common English words, then checks each against the dictionary.  If any
    are unknown the gate requires human review.
    """
    combined = hook_text + " " + lead_text
    candidates = _extract_capitalized_words(combined)
    unknown = find_unknown_proper_nouns(candidates, dictionary)

    # De-duplicate while preserving first-seen order
    seen: Set[str] = set()
    deduped: List[str] = []
    for w in unknown:
        if w not in seen:
            seen.add(w)
            deduped.append(w)

    return GateResult(
        requires_review=len(deduped) > 0,
        unknown_words=deduped,
    )
