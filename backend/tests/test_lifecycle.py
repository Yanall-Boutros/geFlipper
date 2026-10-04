import asyncio

from app.core.lifecycle import LifecycleTask


class Sleeper(LifecycleTask):
    name = "sleeper"

    def __init__(self):
        super().__init__()
        self.started = asyncio.Event()
        self.cancelled = False
        self.runs = 0

    async def run(self):
        self.runs += 1
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


async def test_start_runs_task():
    task = Sleeper()
    assert not task.running
    task.start()
    await asyncio.wait_for(task.started.wait(), 1)
    assert task.running
    await task.stop()


async def test_start_twice_is_noop():
    task = Sleeper()
    task.start()
    first = task._task
    task.start()
    assert task._task is first
    await asyncio.wait_for(task.started.wait(), 1)
    assert task.runs == 1
    await task.stop()


async def test_stop_cancels_task():
    task = Sleeper()
    task.start()
    await asyncio.wait_for(task.started.wait(), 1)
    await task.stop()
    assert task.cancelled
    assert not task.running
    assert task._task is None


async def test_stop_without_start_is_noop():
    await Sleeper().stop()


async def test_stop_swallows_task_errors():
    class Failing(LifecycleTask):
        async def run(self):
            raise RuntimeError("boom")

    task = Failing()
    task.start()
    await asyncio.sleep(0)
    await task.stop()
    assert not task.running


async def test_can_restart_after_stop():
    task = Sleeper()
    task.start()
    await asyncio.wait_for(task.started.wait(), 1)
    await task.stop()
    task.started.clear()
    task.start()
    await asyncio.wait_for(task.started.wait(), 1)
    assert task.runs == 2
    await task.stop()
