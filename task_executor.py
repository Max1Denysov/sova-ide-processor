import datetime
import importlib
import logging
import traceback
from dataclasses import dataclass
from time import sleep
from urllib.parse import urljoin

import requests
import sqlalchemy
from nlab import elk
from nlab.db import create_sessionmaker

import settings
from models import Task
from pyqu.core import WorkerData
from pyqu.impl.process.multiproc import MultiprocessingProcessBackend
from pyqu.impl.queue.postgres import QueuePostgresSqlachemyBackend
from pyqu.pyqu import Pyqu
from settings import NLAB_ARM_WS_NOTIFIER_URL
from utils import TaskResult

LOG_TIME_FORMAT = "%H:%M:%S %d.%m.%Y"

log = elk.setup("arm", "job-processor")


@dataclass
class TaskRunArguments(WorkerData):
    task_type: str
    worker_name: str
    task_json_args: list
    task_add_kwargs: dict
    task_add_vars: list
    func: 'typing.Any'  # noqa


EVENT = "task_report"


def send_change_status_notification(namespace, task_id, status, event=None):
    """
    Отправка уведомления об изменении статуса задачи
    """
    try:
        requests.post(
            url=urljoin(NLAB_ARM_WS_NOTIFIER_URL, "send_notification"),
            json={
                "event": event or EVENT,
                "data": {
                    "data": {
                        "task_id": task_id,
                        "status": status,
                    }
                },
                "namespace": "/{}".format(namespace)
            }
        )
    except(requests.exceptions.HTTPError, requests.exceptions.ConnectionError,
           requests.exceptions.Timeout, requests.exceptions.RequestException):
        pass


def switch_failed_tasks(session):
    # TODO: не нашел - где эта функция используется
    session.query(Task).filter(
        Task.status == Task.WORKING
    ).update({"status": Task.FAILED})


def _task_cycle_impl(*, session, worker_name, task_type=None,
                     task_json_args=None,
                     task_add_kwargs=None, task_add_vars=None):

    # log.debug("Cycle: %s, %s", task_type, task_json_args)
    pass_filter_q = [Task.status == Task.ENQUEUED]

    if task_type:
        pass_filter_q.append(Task.type == task_type)

    task_add_vars = task_add_vars or []

    task_json_args = task_json_args or []
    for arg in task_json_args:
        assert isinstance(arg, (tuple, list))
        pass_filter_q.append(Task.args[arg[0]].astext == arg[1])

    task_model = session.query(Task).filter(*pass_filter_q).order_by(
        Task.created
    ).with_for_update().first()

    if not task_model:
        sleep(settings.TASK_RUN_TIME_INTERVAL_SEC)
        return

    task_kwargs = {}
    task_kwargs.update(task_add_kwargs or {})
    task_kwargs.update(**task_model.args)
    if "task_id" in task_add_vars:
        task_kwargs["task_id"] = task_model.task_id

    task_model.status = Task.WORKING
    task_model.locked_by = worker_name  # FIX race to postgres
    task_model.updated = datetime.datetime.now()

    session.add(task_model)
    session.commit()

    send_change_status_notification(
        namespace=task_model.type, task_id=task_model.task_id,
        status=task_model.status
    )

    log.info(f"The task {task_model.task_id} in progress...")

    function = None
    try:
        module_name, function_name = task_model.script.rsplit(".", 1)
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)

    except (ModuleNotFoundError, AttributeError):
        task_model.status = Task.FAILED
        task_model.errortext = traceback.format_exc()
        log.exception(
            "Error in starting",
            extra={
                "script": task_model.script,
                "params": task_model.args,
                "status": task_model.status,
            }
        )

    if function:
        try:
            task_result = function(**task_kwargs)

            if isinstance(task_result, dict):
                # Deprecated logic
                task_model.result = task_result
            elif isinstance(task_result, TaskResult):
                task_model.result = task_result.result
                task_model.extra = task_result.extra
            else:
                raise RuntimeError("Unhandled task result: %s" % task_result)

            task_model.status = Task.FINISHED

        except Exception:
            task_model.status = Task.FAILED
            task_model.errortext = traceback.format_exc()
            log.exception(
                "Error in call",
                extra={
                    "script": task_model.script,
                    "params": task_model.args,
                    "status": task_model.status,
                }
            )

    log.info("Completed task {} with the status {}".format(
        task_model.task_id, task_model.status.upper()))

    task_model.updated = datetime.datetime.now()
    session.add(task_model)
    session.commit()

    send_change_status_notification(
        namespace=task_model.type, task_id=task_model.task_id,
        status=task_model.status
    )


def create_engine():

    sessionmaker = create_sessionmaker(
        env_prefix=settings.POSTGRES_PREFIX
    )
    return sessionmaker


def _task_loop(args: TaskRunArguments):
    paramiko_transport_logger = logging.getLogger('paramiko.transport')
    paramiko_transport_logger.setLevel(logging.INFO)

    RECREATE_SESSION_ERRORS = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.InvalidRequestError,
        sqlalchemy.exc.StatementError,
        sqlalchemy.exc.OperationalError,
    )

    sessionmaker = create_engine()

    # fail working tasks with exact such name
    with sessionmaker() as session:
        session.query(Task).filter(
            Task.status == Task.WORKING,
            Task.locked_by == args.worker_name,
        ).update({
            "status": Task.FAILED,
            "result": {
                "output": "Unexpected fail. Please restart task",
                "success": False, "messages": [],
            }
        })
        session.commit()

    while True:
        try:
            with sessionmaker() as session:
                while True:
                    try:
                        _task_cycle_impl(
                            task_type=args.task_type,
                            worker_name=args.worker_name,
                            task_json_args=args.task_json_args,
                            task_add_kwargs=args.task_add_kwargs,
                            task_add_vars=args.task_add_vars,
                            session=session,
                        )
                    except RECREATE_SESSION_ERRORS:
                        log.exception("Database error")
                        raise

                    except Exception:
                        log.exception("Unhandled error in task cycle")

        except RECREATE_SESSION_ERRORS:
            session.rollback()
            log.exception("Recreate session error")

        except Exception:
            log.exception("Unhandled error in whole loop")


def ok_callback(_):
    pass


def error_callback(e):
    logger = logging.getLogger()
    logger.exception("System exception in task: %s", e)


if __name__ == "__main__":

    # Список датаклассов с аргументами задач для процесса
    run_process_args = [
        TaskRunArguments(
            func=_task_loop,
            task_type="testcase", task_json_args=[],
            task_add_kwargs={}, task_add_vars=[],
            worker_name="testcase",
        ),
        TaskRunArguments(
            func=_task_loop,
            task_type="suite", task_json_args=[],
            task_add_kwargs={}, task_add_vars=[],
            worker_name="suite",
        ),
        TaskRunArguments(
            func=_task_loop,
            task_type="dictionary", task_json_args=[],
            task_add_kwargs={}, task_add_vars=[],
            worker_name="dictionary",
        ),
    ]

    for host_name, host_info in settings.ENGINE_COMPILER_HOSTS.items():

        target = ""
        group = host_info.get("group")
        if host_info["exclusive"]:
            # Процессом будут выполняться только запросы с заданной группой.
            # Может быть названием машины или отдельной группой, если у
            # нас появятся выделенный пул машин на группу.
            target = group if group else host_name
        else:
            assert not group

        run_args = TaskRunArguments(
            func=_task_loop,
            task_type="compiler",
            task_json_args=[("target", target), ],
            task_add_kwargs={"compiler_host": host_name},
            task_add_vars=["task_id"],
            worker_name=f"compiler-{host_name}",
        )
        run_process_args.append(run_args)

    for host_name, host_info in settings.ENGINE_DEPLOY_HOSTS.items():

        target = ""
        group = host_info.get("group")
        if host_info["exclusive"]:
            target = group if group else host_name
        else:
            assert not group

        run_args = TaskRunArguments(
            func=_task_loop,
            task_type="deploy",
            task_json_args=[("target", target), ],
            task_add_kwargs={"target": host_name},
            task_add_vars=["task_id"],
            worker_name=f"deploy-{host_name}",
        )

        run_process_args.append(run_args)

    log.info("Running %d processes", len(run_process_args))
    for args in run_process_args:
        log.info("Running %s", args)
    queue = Pyqu(
        process_backend=MultiprocessingProcessBackend(),
        queue_backend=QueuePostgresSqlachemyBackend(),
    )
    queue.init(run_process_args)
    queue.start_and_wait()
