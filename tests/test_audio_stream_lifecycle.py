"""
Regression: unsynchronized AudioStream.start()/stop() let a stop close and
terminate PortAudio underneath a live capture thread — a native SIGSEGV in
PaUtil_ReadRingBuffer (confirmed by a macOS crash report with TWO capture
threads). start() also set _running=True before open(), poisoning the
singleton forever when the mic open failed.

CI-safe: pyaudio and numpy are stubbed in sys.modules before import when
absent; each test swaps the module-level pyaudio for a fake and uses a
fresh (non-singleton) instance.
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
    Stream=object,
    PyAudio=lambda: types.SimpleNamespace(open=lambda **k: None,
                                          terminate=lambda: None),
)
_stub_module(
    "numpy",
    int16="int16",
    frombuffer=lambda data, dtype=None: [],
    array=lambda *a, **k: types.SimpleNamespace(tobytes=lambda: b""),
    ndarray=object,
    float32="float32",
)

import assistant.input.audio_stream as as_mod  # noqa: E402


class FakeStream:
    """Records reader concurrency and close-while-reading violations."""

    max_concurrent_readers = 0
    closed_while_reading = 0

    def __init__(self):
        self._readers = 0
        self._lock = threading.Lock()
        self.closed = False

    def read(self, n, exception_on_overflow=False):
        with self._lock:
            self._readers += 1
            FakeStream.max_concurrent_readers = max(
                FakeStream.max_concurrent_readers, self._readers)
        try:
            if self.closed:
                raise RuntimeError("read on closed stream")
            time.sleep(0.02)
            return b"\x00" * (n * 2)
        finally:
            with self._lock:
                self._readers -= 1

    def stop_stream(self):
        pass

    def close(self):
        with self._lock:
            if self._readers > 0:
                FakeStream.closed_while_reading += 1
            self.closed = True


class FakePyAudioModule:
    paInt16 = 8

    def __init__(self, open_raises=False):
        self.open_raises = open_raises
        self.streams = []
        mod_self = self

        class _PA:
            def open(pa_self, **kwargs):
                if mod_self.open_raises:
                    raise OSError("mic unavailable")
                s = FakeStream()
                mod_self.streams.append(s)
                return s

            def terminate(pa_self):
                pass

        self.PyAudio = _PA


@pytest.fixture
def fresh_stream(monkeypatch):
    FakeStream.max_concurrent_readers = 0
    FakeStream.closed_while_reading = 0

    fake_pa = FakePyAudioModule()
    monkeypatch.setattr(as_mod, "pyaudio", fake_pa)

    inst = as_mod.AudioStream.__new__(as_mod.AudioStream)
    inst._initialized = False
    inst.__init__()

    yield inst, fake_pa

    inst._running = False
    inst.stop()


def test_start_failure_rolls_back_cleanly(monkeypatch):
    fake_pa = FakePyAudioModule(open_raises=True)
    monkeypatch.setattr(as_mod, "pyaudio", fake_pa)

    inst = as_mod.AudioStream.__new__(as_mod.AudioStream)
    inst._initialized = False
    inst.__init__()

    with pytest.raises(OSError):
        inst.start()

    assert inst._running is False, "poisoned _running=True regression"
    assert inst._stream is None and inst._audio is None

    # Recovery: a later start with a working mic must succeed
    fake_pa.open_raises = False
    inst.start()
    assert inst._running is True
    assert inst.stop() is True


def test_stop_never_closes_under_a_live_reader(fresh_stream):
    inst, fake_pa = fresh_stream
    inst.start()
    time.sleep(0.1)          # capture loop is actively reading

    assert inst.stop() is True
    assert FakeStream.closed_while_reading == 0, \
        "stream closed while capture thread was inside read() — the SIGSEGV shape"
    assert inst._thread is None


def test_rapid_start_stop_cycles_single_reader(fresh_stream):
    inst, fake_pa = fresh_stream
    for _ in range(10):
        inst.start()
        time.sleep(0.03)
        assert inst.stop() is True

    assert FakeStream.max_concurrent_readers <= 1, \
        "two concurrent capture readers existed — the crash-report shape"
    assert FakeStream.closed_while_reading == 0


def test_start_is_idempotent_while_running(fresh_stream):
    inst, fake_pa = fresh_stream
    inst.start()
    inst.start()             # second call must be a warning no-op
    assert len(fake_pa.streams) == 1
    assert inst.stop() is True
