import asyncio

import pytest

from app.services.collectors import base
from app.services.collectors.base import BaseCollector


class FakeSessionLocal:
    """Stands in for SessionLocal: an async context manager yielding a sentinel."""
    def __init__(self):
        self.session = object()
        self.opened = 0
        self.closed = 0

    def __call__(self):
        return self

    async def __aenter__(self):
        self.opened += 1
        return self.session

    async def __aexit__(self, *exc):
        self.closed += 1


@pytest.fixture
def sessions(monkeypatch):
    fake = FakeSessionLocal()
    monkeypatch.setattr(base, "SessionLocal", fake)
    return fake


class Recorder(BaseCollector):
    name = "recorder"
    interval = 0

    def __init__(self, stop_after: int, fail_on: tuple[int, ...] = ()):
        super().__init__()
        self.stop_after = stop_after
        self.fail_on = fail_on
        self.sessions = []
        self.done = asyncio.Event()

    async def collect(self, db):
        self.sessions.append(db)
        if len(self.sessions) >= self.stop_after:
            self.done.set()
        if len(self.sessions) in self.fail_on:
            raise RuntimeError("collection failed")


async def test_run_once_opens_and_closes_session(sessions):
    collector = Recorder(stop_after=1)
    await collector.run_once()
    assert collector.sessions == [sessions.session]
    assert (sessions.opened, sessions.closed) == (1, 1)


async def test_run_repeats_collection(sessions):
    collector = Recorder(stop_after=3)
    collector.start()
    await asyncio.wait_for(collector.done.wait(), 1)
    await collector.stop()
    assert len(collector.sessions) >= 3
    assert sessions.opened == sessions.closed


async def test_failed_run_is_logged_and_retried(sessions, caplog):
    collector = Recorder(stop_after=3, fail_on=(1, 2))
    collector.start()
    await asyncio.wait_for(collector.done.wait(), 1)
    await collector.stop()
    assert "collector recorder failed" in caplog.text
    assert len(collector.sessions) >= 3


async def test_run_sleeps_for_remaining_interval(sessions, monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        raise asyncio.CancelledError  # end the loop after one pass

    monkeypatch.setattr(base.asyncio, "sleep", fake_sleep)
    collector = Recorder(stop_after=1)
    collector.interval = 60
    with pytest.raises(asyncio.CancelledError):
        await collector.run()
    assert len(sleeps) == 1
    assert 59 < sleeps[0] <= 60
