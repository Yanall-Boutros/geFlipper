# Base class for long-lived tasks that run for the lifetime of the FastAPI app.
# main.py's lifespan hook calls start() on startup and stop() on shutdown.
import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LifecycleTask(ABC):
    name: str = "task"

    def __init__(self):
        self._task: asyncio.Task | None = None

    @abstractmethod
    async def run(self) -> None:
        """The task body. Runs until it returns or is cancelled by stop()."""

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        """Schedule run() on the event loop. Calling it twice is a no-op."""
        if self.running:
            return
        logger.info("starting task %s", self.name)
        self._task = asyncio.create_task(self.run(), name=self.name)

    async def stop(self) -> None:
        """Cancel the task and wait for it to finish."""
        if self._task is None:
            return
        logger.info("stopping task %s", self.name)
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None
