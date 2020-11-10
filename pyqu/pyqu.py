""" Python Postgres Queue """
import atexit
import logging
from typing import List

from pyqu.core import ProcessBackend, QueueBackend, WorkerContext

logger = logging.getLogger()


class Pyqu:
    def __init__(self, queue_backend: QueueBackend,
                 process_backend: ProcessBackend):

        self._queue_backend = queue_backend
        self._process_backend = process_backend

        atexit.register(self.terminate)

    def init(self, all_worker_args: List[WorkerContext]):
        self._process_backend.init(all_worker_args)

    def terminate(self):
        self._process_backend.terminate()

    def start(self):
        self._process_backend.start()

    def handle_cycle(self):
        self._process_backend.handle_cycle()

    def wait(self, timeout=None):
        self._process_backend.wait(timeout=timeout)

    def start_and_wait(self):
        self.start()
        self.wait()
