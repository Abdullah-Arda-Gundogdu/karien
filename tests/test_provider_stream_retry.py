"""
Regression: provider retry logic was dead code for streaming calls — calling
a generator function only CREATES the generator, so the try/except around it
never caught anything and errors crashed the caller mid-conversation.
"""
from assistant.brain.providers.base import StreamChunk
from assistant.brain.providers.openai_provider import OpenAIProvider


def _provider():
    # No api_key → no client; we monkeypatch _stream_completion directly
    return OpenAIProvider(model="gpt-4o-mini")


def test_stream_error_before_output_retries_then_falls_back():
    p = _provider()
    attempts = []

    def failing(kwargs):
        attempts.append(1)
        raise RuntimeError("boom")
        yield  # pragma: no cover — makes this a generator function

    p._stream_completion = failing
    chunks = list(p._stream_with_retry({}, retry_count=3, retry_delay=0))

    assert len(attempts) == 3, "should retry up to retry_count before giving up"
    assert chunks and chunks[-1].chunk_type == "content"
    assert "Beynime" in chunks[-1].content, "must end with the graceful fallback"


def test_stream_error_after_partial_output_does_not_duplicate():
    p = _provider()
    attempts = []

    def partial(kwargs):
        attempts.append(1)
        yield StreamChunk(chunk_type="content", content="Merha")
        raise RuntimeError("connection dropped")

    p._stream_completion = partial
    chunks = list(p._stream_with_retry({}, retry_count=3, retry_delay=0))

    assert len(attempts) == 1, "retry after partial output would duplicate content"
    contents = [c.content for c in chunks if c.chunk_type == "content"]
    assert contents[0] == "Merha"
    assert "Beynime" in contents[-1]


def test_successful_stream_passes_through():
    p = _provider()

    def ok(kwargs):
        yield StreamChunk(chunk_type="content", content="a")
        yield StreamChunk(chunk_type="content", content="b")

    p._stream_completion = ok
    chunks = list(p._stream_with_retry({}, retry_count=3, retry_delay=0))
    assert [c.content for c in chunks] == ["a", "b"]
