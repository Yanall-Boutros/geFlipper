from fastapi import FastAPI

from app import main
from app.core.lifecycle import LifecycleTask
from app.services.rswiki.priceData import RSWikiPriceData


def test_build_tasks_with_collectors(monkeypatch):
    monkeypatch.setattr(main.settings, "ENABLE_COLLECTORS", True)
    tasks = main.build_tasks()
    assert [type(task) for task in tasks] == [RSWikiPriceData]


def test_build_tasks_without_collectors(monkeypatch):
    monkeypatch.setattr(main.settings, "ENABLE_COLLECTORS", False)
    assert main.build_tasks() == []


class FakeTask(LifecycleTask):
    def __init__(self):
        super().__init__()
        self.events = []

    async def run(self):
        pass

    def start(self):
        self.events.append("start")

    async def stop(self):
        self.events.append("stop")


async def test_lifespan_starts_and_stops_tasks(monkeypatch):
    tasks = [FakeTask(), FakeTask()]
    monkeypatch.setattr(main, "build_tasks", lambda: tasks)
    app = FastAPI()

    async with main.lifespan(app):
        assert app.state.tasks == tasks
        assert all(task.events == ["start"] for task in tasks)

    assert all(task.events == ["start", "stop"] for task in tasks)


def test_api_is_mounted_under_v1():
    paths = set(main.app.openapi()["paths"])
    assert {"/api/v1/health", "/api/v1/price-data"} <= paths
