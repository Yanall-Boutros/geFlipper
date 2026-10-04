from unittest.mock import MagicMock

from app.api import deps


class FakeSessionContext:
    def __init__(self, session):
        self.session = session
        self.exited = False

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        self.exited = True


async def test_get_db_yields_session_and_closes_context(monkeypatch):
    session = MagicMock()
    ctx = FakeSessionContext(session)
    monkeypatch.setattr(deps, "SessionLocal", lambda: ctx)

    gen = deps.get_db()
    assert await gen.__anext__() is session
    assert not ctx.exited

    await gen.aclose()
    assert ctx.exited
