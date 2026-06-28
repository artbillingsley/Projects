import pytest
from pathlib import Path


SAMPLE_YAML = """
proper_nouns:
  Hormuz: '<phoneme alphabet="ipa" ph="hɔːɹˈmuːz">Hormuz</phoneme>'
  COGNOSCERE: '<phoneme alphabet="ipa" ph="kɒɡˈnɒʃɛɹeɪ">COGNOSCERE</phoneme>'

acronyms:
  speak_as_word:
    - NATO
    - CENTCOM
  spell_out:
    - ICE
    - SEC
"""


def test_load_dictionary(tmp_path):
    from src.lib.pronunciation import load_dictionary

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)

    d = load_dictionary(str(yaml_file))
    assert "Hormuz" in d.proper_nouns
    assert "NATO" in d.speak_as_word
    assert "ICE" in d.spell_out


def test_inject_ssml_replaces_known_nouns(tmp_path):
    from src.lib.pronunciation import load_dictionary, inject_ssml

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    text = "Iran struck near the Strait of Hormuz."
    result = inject_ssml(text, d)
    assert '<phoneme alphabet="ipa"' in result
    assert "hɔːɹˈmuːz" in result


def test_inject_ssml_leaves_unknown_words_alone(tmp_path):
    from src.lib.pronunciation import load_dictionary, inject_ssml

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    text = "Biden spoke to reporters."
    result = inject_ssml(text, d)
    assert result == text


def test_find_unknown_proper_nouns(tmp_path):
    from src.lib.pronunciation import load_dictionary, find_unknown_proper_nouns

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    words_in_script = ["Hormuz", "Netanyahu", "Pulte", "CENTCOM"]
    unknown = find_unknown_proper_nouns(words_in_script, d)
    assert "Netanyahu" in unknown
    assert "Pulte" in unknown
    assert "Hormuz" not in unknown
    assert "CENTCOM" not in unknown


def test_proper_noun_gate_flags_unknown_in_hook(tmp_path):
    from src.lib.pronunciation import load_dictionary, check_proper_noun_gate

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    hook_text = "Netanyahu's war near Hormuz escalates."
    lead_text = "Iran struck U.S. bases."

    result = check_proper_noun_gate(hook_text, lead_text, d)
    assert result.requires_review is True
    assert "Netanyahu" in result.unknown_words


def test_proper_noun_gate_passes_when_all_known(tmp_path):
    from src.lib.pronunciation import load_dictionary, check_proper_noun_gate

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    hook_text = "The Strait of Hormuz is a shooting gallery."
    lead_text = "COGNOSCERE reports the latest."

    result = check_proper_noun_gate(hook_text, lead_text, d)
    assert result.requires_review is False
    assert result.unknown_words == []
