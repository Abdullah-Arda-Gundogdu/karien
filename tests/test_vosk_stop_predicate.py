"""
Regression: listen_for_wakeword looped forever with no stop predicate,
making voice-service shutdown windows unbounded — the enabler of the
mute/unmute PortAudio SIGSEGV. It must now return False promptly on
request_stop(), refuse concurrent entry, and abort error backoffs.

CI-safe: pyaudio/vosk are stubbed in sys.modules before import when absent;
each test uses a fresh VoskSTT instance with fake stream/recognizer, so no
audio hardware or model is touched.
"""
import importlib
import sys
import threading
import time
import types

import pytest


def _stub_module(name, **attrs):
    try:
        importlib.import_module(name)
    except ImportError:
        sys.modules[name] = types.SimpleNamespace(**attrs)


_stub_module(
    "pyaudio",
    paInt16=8,
    PyAudio=lambda: types.SimpleNamespace(open=lambda **k: None,
                                          terminate=lambda: None),
)
_stub_module("vosk", Model=lambda path: object(), KaldiRecognizer=lambda *a: object())

import assistant.input.vosk_stt as vosk_mod  # noqa: E402


class FakeRecognizer:
    def __init__(self, *args):
        pass

    def AcceptWaveform(self, data):
        return False

    def PartialResult(self):
        return '{"partial": ""}'

    def Result(self):
        return '{"text": ""}'


class FakeStream:
    def __init__(self, read_delay=0.05, fail=False):
        self.read_delay = read_delay
        self.fail = fail
        self.closed = False
        self.reads = 0

    def start_stream(self):
        pass

    def read(self, n, exception_on_overflow=False):
        if self.fail:
            raise RuntimeError("boom")
        self.reads += 1
        time.sleep(self.read_delay)
        return b"\x00" * (n * 2)

    def stop_stream(self):
        pass

    def close(self):
        self.closed = True


class FakeAudio:
    def __init__(self, stream_factory):
        self._factory = stream_factory
        self.opened = []

    def open(self, **kwargs):
        s = self._factory()
        self.opened.append(s)
        return s


@pytest.fixture
def stt(monkeypatch):
    monkeypatch.setattr(vosk_mod, "KaldiRecognizer", FakeRecognizer)
    inst = vosk_mod.VoskSTT.__new__(vosk_mod.VoskSTT)
    inst.model = object()
    inst.recognizer = None
    inst.stream = None
    inst.use_vad = False
    inst._stop_event = threading.Event()
    inst._listen_lock = threading.Lock()
    inst.audio = FakeAudio(lambda: FakeStream())
    return inst


def _run_listener(inst, results):
    results.append(inst.listen_for_wakeword(["hey kariyer"]))


def test_stop_makes_listener_return_false_promptly(stt):
    results = []
    t = threading.Thread(target=_run_listener, args=(stt, results), daemon=True)
    t.start()
    time.sleep(0.2)          # let it open the stream and start reading

    start = time.time()
    stt.request_stop()
    t.join(timeout=1.5)

    assert not t.is_alive(), "listener must exit after request_stop"
    assert results == [False]
    assert (time.time() - start) < 1.5
    assert stt.audio.opened[0].closed, "stream must be cleaned up on stop"


def test_pre_set_stop_returns_immediately_without_opening_stream(stt):
    stt.request_stop()
    assert stt.listen_for_wakeword(["hey kariyer"]) is False
    assert stt.audio.opened == []


def test_reentrancy_guard_refuses_second_listener(stt):
    results = []
    t = threading.Thread(target=_run_listener, args=(stt, results), daemon=True)
    t.start()
    time.sleep(0.2)

    # Second concurrent call must bounce off immediately (no second stream)
    assert stt.listen_for_wakeword(["hey kariyer"]) is False
    assert len(stt.audio.opened) == 1

    stt.request_stop()
    t.join(timeout=1.5)
    assert not t.is_alive()


def test_stop_during_error_backoff_returns(stt):
    stt.audio = FakeAudio(lambda: FakeStream(fail=True))
    results = []
    t = threading.Thread(target=_run_listener, args=(stt, results), daemon=True)
    t.start()
    time.sleep(0.3)          # it should be inside the error backoff wait

    stt.request_stop()
    t.join(timeout=1.5)

    assert not t.is_alive(), "stop must interrupt the error backoff"
    assert results == [False]


def test_reset_stop_allows_fresh_listen(stt):
    stt.request_stop()
    assert stt.listen_for_wakeword(["hey kariyer"]) is False
    stt.reset_stop()
    assert stt.stop_requested is False
