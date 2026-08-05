"""
Regression: the Stop button ("Durdur") only drained the queue — an item the
worker had ALREADY dequeued (still waiting on the TTS API) played anyway
right after the stop. The playback-epoch mechanism cancels those too.

CI-safe: pygame is stubbed per test (tts.py imports pygame inside methods,
so sys.modules patching works even when real pygame is installed), and the
TTS API is a gated fake OpenAI client so the REAL _generate_audio logic
(including the stale-cleanup finally block) is what gets exercised.
"""
import sys
import tempfile
import threading
import time
import types
import uuid
from pathlib import Path

import pytest


def _make_pygame_stub():
    calls = {"play": 0, "stop": 0}
    music = types.SimpleNamespace(
        load=lambda p: None,
        play=lambda: calls.__setitem__("play", calls["play"] + 1),
        stop=lambda: calls.__setitem__("stop", calls["stop"] + 1),
        unload=lambda: None,
        get_busy=lambda: False,
    )
    mod = types.SimpleNamespace(
        mixer=types.SimpleNamespace(init=lambda: None, music=music),
        time=types.SimpleNamespace(
            Clock=lambda: types.SimpleNamespace(tick=lambda n: time.sleep(0.01))
        ),
    )
    mod._calls = calls
    return mod


class _GatedFakeOpenAI:
    """audio.speech.create blocks on a gate, then writes a real temp mp3."""

    def __init__(self, gate):
        outer = self

        class _Speech:
            def create(self, model, voice, input):
                gate.wait(timeout=5)

                class _Resp:
                    def stream_to_file(self, path):
                        Path(path).write_bytes(b"fake-mp3")

                return _Resp()

        self.audio = types.SimpleNamespace(speech=_Speech())
        self.gate = gate


@pytest.fixture
def tts_instance(monkeypatch):
    stub = _make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", stub)

    from assistant.output.tts import TextToSpeech

    gate = threading.Event()
    t = TextToSpeech()
    t.provider = "openai"
    t.client = _GatedFakeOpenAI(gate)

    yield t, stub, gate

    gate.set()
    t.stop()


def _wait_until(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def _temp_mp3_count():
    return len(list(Path(tempfile.gettempdir()).glob("tts_*.mp3")))


def test_stop_discards_item_still_in_generation(tts_instance):
    t, stub, gate = tts_instance
    baseline = _temp_mp3_count()

    t.speak_async("uzun bir cümle")
    time.sleep(0.3)          # let the worker dequeue and park on the gate
    t.stop_playback()        # stop lands BEFORE generation finishes
    gate.set()               # now the TTS API "returns"

    assert _wait_until(lambda: t.queue.unfinished_tasks == 0)
    assert stub._calls["play"] == 0, "stale item must never play"
    assert _wait_until(lambda: _temp_mp3_count() <= baseline), \
        "stale generation must clean up its temp file"


def test_is_playing_false_immediately_after_stop(tts_instance):
    t, stub, gate = tts_instance
    t.speak_async("bir şey")
    time.sleep(0.2)
    t.stop_playback()
    assert t.is_playing() is False


def test_new_speech_after_stop_still_plays(tts_instance):
    t, stub, gate = tts_instance
    t.speak_async("iptal edilecek")
    time.sleep(0.2)
    t.stop_playback()

    gate.set()               # everything from here generates instantly
    t.speak_async("bu çalmalı")
    assert _wait_until(lambda: stub._calls["play"] == 1), \
        "post-stop speech must play exactly once"


def test_durdur_repro_two_items_both_cancelled(tts_instance):
    """The exact live-test shape: orchestrator queues first sentence +
    remainder back-to-back, user hits Durdur while the first generates."""
    t, stub, gate = tts_instance
    baseline = _temp_mp3_count()

    t.speak_async("ilk cümle.")
    t.speak_async("kalan her şey")
    time.sleep(0.3)
    t.stop_playback()
    gate.set()

    assert _wait_until(lambda: t.queue.unfinished_tasks == 0)
    assert stub._calls["play"] == 0
    assert _wait_until(lambda: _temp_mp3_count() <= baseline)
    assert t.is_playing() is False
