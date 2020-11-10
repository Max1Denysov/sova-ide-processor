import logging
import os
import tempfile
from pathlib import Path

from engine.task import DeployTask, DeployTaskResult, EngineTaskResult
from models import ComplectRevision

logger = logging.getLogger(__name__)


class EngineDeployProcess(EngineTaskResult):
    """
    Deals with the deploy process and stores result
    """

    def __init__(self, factory: 'EngineFactory', task: DeployTask,  # noqa
                 create_session):
        self._factory = factory
        self._task = task
        self._result = DeployTaskResult()

        self._create_session = create_session

    def execute(self):
        """
        Runs deploy and returns result
        :return:
        """
        try:
            self._execute()
        except:  # noqa
            logger.exception("Unhandled deploy error")

        return self._result

    @property
    def result(self):
        return self._result

    def _execute(self):

        logger.debug('_execute: START')

        # Looking for binary storage
        with self._create_session() as session:
            complect_revision = (session.query(ComplectRevision).
                                 get(self._task.complect_revision_id))

            logger.debug(
                '_execute: From table ComplectRevision received '
                f'complect_revision={complect_revision}'
            )

            if not complect_revision:
                self._result.output = ("No such complect_revision_id=%s"
                                       % self._task.complect_revision_id)
                logger.debug('_execute: END - No such complect_revision')
                return

            self._result.complect_id = complect_revision.complect_id

            if not complect_revision.binary_path:
                self._result.output = ("No deployed binary path"
                                       % self._task.complect_revision_id)
                logger.debug(
                    '_execute: END - No deployed binary path _task.'
                    f'complect_revision_id={self._task.complect_revision_id}'
                )
                return

            paths = complect_revision.binary_path.split(":")

        source_engine, source_remote_path = paths

        # Download binary file
        source_engine = self._factory.create_compiler_backend(
            source_engine,
        )
        source_engine.connect()
        logger.debug(f'_execute: Connected to "{source_remote_path}"')

        local_path = Path(tempfile.mkdtemp())
        local_binary_path = local_path / Path(source_remote_path).name
        logger.debug(
            f'_execute: Created local_binary_path="{local_binary_path}"'
        )

        source_engine.get_file(source_remote_path, local_binary_path)
        logger.debug(
            f'_execute: Downloaded from remote "{source_remote_path}"'
            f' to "{local_binary_path}"'
        )
        source_engine.close()  # TODO: with block

        target_engine = self._factory.create_deployer_backend(
            self._task.target,
        )
        target_engine.connect()
        logger.debug('_execute: target_engine.connect() Ok')

        # Upload binary data
        upload_result = uploaded_binary = target_engine.upload(local_path)
        if upload_result.result.code != 0:
            logger.debug('_execute: END - upload_result.result.code != 0')
            return
        logger.debug('_execute: target_engine.upload(local_path) Ok')

        update_result = target_engine.update(uploaded_binary.complect_path)
        if update_result.result.code != 0:
            logger.debug('_execute: END - update_result.result.code != 0')
            return
        logger.debug('_execute: target_engine.update() Ok')

        restart_result = target_engine.restart()
        if restart_result.result.code != 0:
            logger.debug('_execute: END - restart_result.result.code != 0')
            return
        logger.debug('_execute: ...target_engine.restart() Ok')

        target_engine.close()  # TODO: with block

        # Удалим файлы и папки старше недели на локальном диске
        # (для освобождения места)
        archive_folder_path = local_path.parent
        cmd_delete = 'find %s -mtime +%s -delete' % (archive_folder_path, 7)
        cmd_exit_code = os.system(cmd_delete)
        logger.info(
            f'_execute - *Deleted* local arch, cmd: "{cmd_delete}", '
            f'cmd_exit_code:"{cmd_exit_code}"'
            )

        self._result.success = True

        logger.debug('_execute: END successful')
