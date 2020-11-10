import logging
import multiprocessing
import time
from typing import List

from pyqu.core import ProcessBackend, WorkerContext, WorkerData

logger = logging.getLogger()


class MultiprocessingWorker(WorkerData):
    def __init__(self, worker_args: WorkerContext):
        self._worker_args = worker_args
        self._process = self._start_process(worker_args)

    def start(self):
        self._process.start()
        logger.debug(
            "Start worker: pid=%s; %s", self._process.pid, self._worker_args
        )

    def ensure_alive(self):
        if not self._process.is_alive():
            logger.info(
                "Restart worker: exitcode: %s; %s", self._process.exitcode,
                self._worker_args
            )
            self._process = self._start_process(self._worker_args)
            self._process.start()

    def restart(self):
        self._process = self._start_process(self._worker_args)
        self._process.start()

    def terminate(self):
        if self._process.is_alive():
            self._process.terminate()

    def _start_process(self, worker_args):
        proc = multiprocessing.Process(target=worker_args.func,
                                       args=(worker_args,))
        proc.daemon = True
        return proc


class MultiprocessingProcessBackend(ProcessBackend):
    def __init__(self):
        self._processes: List[MultiprocessingWorker] = []

    def init(self, all_worker_args: List[WorkerContext]):
        self._init_processes(all_worker_args)

    def start(self):
        for proc in self._processes:
            proc.start()

    def wait(self, timeout=None):
        start = time.time()
        while True:
            self.handle_cycle()
            time.sleep(0.1)
            now = time.time()

            if timeout is not None and now - start >= timeout:
                break

    def terminate(self):
        for proc in self._processes:
            proc.terminate()

    def handle_cycle(self):
        for proc in self._processes:
            proc.ensure_alive()

    def _init_processes(self, all_worker_args):
        for args in all_worker_args:
            worker_process = MultiprocessingWorker(args)
            self._processes.append(worker_process)
