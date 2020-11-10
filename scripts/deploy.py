import logging

import settings
from engine.factory import EngineFactory
from engine.task import DeployTask, DeployTaskResult
from engine.tasks.deploy import EngineDeployProcess
from nlab.db import create_sessionmaker
from utils import TaskResult

logger = logging.getLogger()


def run(complect_revision_id, target, task_id):
    """ Выполнение деплоя """
    logger.info(f"Running deploy: task_id={task_id} "
                f"target={target}")

    engine_factory = EngineFactory()

    create_session = create_sessionmaker(env_prefix=settings.POSTGRES_PREFIX)

    task = DeployTask(
        complect_revision_id=complect_revision_id,
        target=target,
    )
    process = EngineDeployProcess(
        factory=engine_factory,
        task=task,
        create_session=create_session,
    )
    result: DeployTaskResult = process.execute()

    output_result = {
        "output": result.output if result else "",
        "messages": [],
        "success": result.success if result else False,
    }

    extra = {
        "complect_revision_id": complect_revision_id,
        "complect_id": result.complect_id if result else None,
    }

    return TaskResult(result=output_result, extra=extra)
