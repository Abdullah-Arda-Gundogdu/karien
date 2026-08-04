"""
Regression: small local models invent mood tags like [Empati] that the orb
face and VTube Studio hotkeys cannot render.
"""
from assistant.brain.synthesizer import normalize_mood_tag, VALID_MOODS


def test_valid_tag_is_kept():
    assert normalize_mood_tag("[happy] Süper!") == "[happy] Süper!"


def test_invalid_tag_becomes_neutral():
    assert normalize_mood_tag("[Empati] Anlıyorum.") == "[neutral] Anlıyorum."


def test_uppercase_valid_tag_is_lowercased():
    assert normalize_mood_tag("[SAD] Off...") == "[sad] Off..."


def test_missing_tag_is_prepended():
    assert normalize_mood_tag("Merhaba!") == "[neutral] Merhaba!"


def test_empty_input():
    assert normalize_mood_tag("") == "[neutral]"


def test_all_nine_moods_are_valid():
    assert VALID_MOODS == {
        "neutral", "happy", "sad", "annoyed", "embarrassed",
        "proud", "curious", "excited", "sleepy",
    }
