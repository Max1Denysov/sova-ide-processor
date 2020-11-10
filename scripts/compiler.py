import logging
from pathlib import Path

import settings
from engine.factory import EngineFactory
from engine.preprocessors.arm1.preprocessor import Arm1Preprocessor
from engine.task import CompilerTask, CompilerTaskResult
from engine.tasks.compiler import (EngineCompilerProcess,
                                   create_complect_revision,
                                   format_output_result)
from nlab.rpc.client import WebClient
from utils import TaskResult

logger = logging.getLogger()


def run(complect_id, target, compiler_host, task_id, try_create_revision):
    """ Выполнение компиляции """
    root_path = Path("/var/tmp")
    root_path.mkdir(mode=0o775, parents=True, exist_ok=True)

    task = CompilerTask(
        complect_id=complect_id,
        target=target,
        compiler_host=compiler_host,
        do_upload=True,
        do_compile=True,
        do_update=True,
        strict=True,
        task_id=task_id,
        try_create_revision=try_create_revision,
    )

    engine_factory = EngineFactory()
    backend = engine_factory.create_compiler_backend(compiler_host)

    gateway_client = WebClient(settings.GATEWAY_URL)
    preprocessor = Arm1Preprocessor(gateway_client=gateway_client)

    process = EngineCompilerProcess(
        preprocessor=preprocessor,
        backend=backend,
        task=task,
        root_path=root_path
    )
    result: CompilerTaskResult = process.execute()

    output_result = format_output_result(result, gateway_client)

    extra = {
        "complect_id": task.complect_id,
    }

    logger.info("Got output result: %s", output_result)

    if task.try_create_revision and result.engine_complect:
        revision_result = create_complect_revision(
            remote_path=result.engine_complect.remote_path,
            compiler_host=task.compiler_host,
            complect_id=task.complect_id,
        )

        output_result.update(revision_result)

        extra["complect_revision_id"] = revision_result["complect_revision_id"]

    return TaskResult(result=output_result, extra=extra)
