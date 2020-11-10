from abc import ABC, abstractmethod
from typing import List


class WorkerContext:
    def __init__(self, func):
        self.func = func


class WorkerData:
    def __init__(self, worker_args: WorkerContext):
        self._worker_args = worker_args


class ProcessBackend(ABC):
    @abstractmethod
    def init(self, all_worker_args: List[WorkerContext]):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def terminate(self):
        pass

    @abstractmethod
    def handle_cycle(self):
        pass

    @abstractmethod
    def wait(self, timeout=None):
        pass


class QueueBackend(ABC):
    pass
