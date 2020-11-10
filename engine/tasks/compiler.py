import logging
import os
import shutil
import tempfile
import traceback
from pathlib import Path

from components import ComplectRevisionRpc
from engine.backend import EngineBackend
from engine.engine_output_parser import EngineOutput, parse_engine_output,\
    load_client_data
from engine.preprocessor import Preprocessor
from engine.task import CompilerTaskResult, CompilerTask, ErrorWithTraceback
from nlab.rpc.client import WebClient
from nlab.service import Tracer
from task_executor import create_engine

logger = logging.getLogger(__name__)


class EngineCompilerProcess:
    """
    Deals with the compiler process and stores result
    """

    def __init__(self, *, preprocessor: Preprocessor, backend: EngineBackend,
                 task: CompilerTask, root_path: Path):
        self._preprocessor: Preprocessor = preprocessor
        self._backend: EngineBackend = backend
        self._task = task
        self._result = CompilerTaskResult()
        self._root_path = root_path

    def execute(self):
        """
        Runs preprocessor, compiler and returns result
        :return:
        """
        try:
            self._execute()
        except Exception as e:
            logger.exception("Unhandled compilation error")
            self._result.exc_result = ErrorWithTraceback(
                error=e, traceback=traceback.format_exc()
            )

        return self.result

    @property
    def result(self):
        return self._result

    def _execute(self):

        logger.debug('_execute: START')

        logger.debug('_execute: self._create_base_dir()')

        base_path = self._create_base_dir()

        logger.debug('_execute: self._backend.connect()')
        self._backend.connect()

        logger.debug('_execute: self._preprocessor.download()')
        download_result = self._preprocessor.download(
            base_path,
            complect_id=self._task.complect_id,
        )
        self._result.php_process_result = download_result.result
        if download_result.result.code != 0 or download_result.result.err:
            logger.debug(
                '_execute: END - download_result.result.code != 0 or err'
            )
            return

        base_path = download_result.base_path

        logger.debug('_execute: self._preprocessor.preprocess()')
        preprocess_result = self._preprocessor.preprocess(base_path)
        self._result.perl_process_result = preprocess_result.result

        if not self._task.do_upload:
            logger.debug('_execute: END - not self._task.do_upload')
            return
        if preprocess_result.result.code != 0 or preprocess_result.result.err:
            logger.debug('_execute: END - preprocess_result.result.code != 0')
            return

        logger.debug('_execute: self._backend.upload()')
        upload_result = self._backend.upload(base_path)
        complect_path = upload_result.complect_path
        self._result.upload_result = upload_result.result
        self._result.engine_complect = complect_path

        if not self._task.do_compile:
            logger.debug('_execute: END - not self._task.do_compile')
            return
        if upload_result.result.code != 0:
            logger.debug('_execute: END - upload_result.result.code != 0')
            return

        logger.debug('_execute: self._backend.compile()')
        compile_result = self._backend.compile(complect_path)
        self._result.compile_result = compile_result.result

        if not self._task.do_update:
            logger.debug('_execute: END - not self._task.do_update')
            return
        if compile_result.result.code != 0:
            logger.debug('_execute: END - compile_result.result.code != 0')
            return

        logger.debug('_execute: self._backend.update()')
        update_result = self._backend.update(complect_path)
        self._result.update_result = update_result.result

        if update_result.result.code != 0:
            logger.debug('_execute: END - update_result.result.code != 0')
            return

        logger.debug('_execute: self._backend.restart()')
        restart_result = self._backend.restart()
        self._result.restart_result = restart_result.result
        if restart_result.result.code != 0:
            logger.debug('_execute: END - restart_result.result.code != 0')
            return

        logger.debug('_execute: self._backend.close()')
        self._backend.close()

        # Удалим файлы и папки старше недели на локальном диске
        # (для освобождения места)
        archive_folder_path = Path(self._root_path)
        cmd_delete = 'find %s -mtime +%s -delete' % (archive_folder_path, 7)
        cmd_exit_code = os.system(cmd_delete)
        logger.info(
            f'_execute - *Deleted* local arch, cmd: "{cmd_delete}", '
            f'cmd_exit_code:"{cmd_exit_code}"'
            )

        logger.debug('_execute: END successful')

    def _create_base_dir(self):

        base_path = Path(tempfile.mkdtemp(dir=self._root_path))
        shutil.rmtree(base_path, ignore_errors=True)
        base_path.mkdir(exist_ok=True)
        logger.debug("Creating %s", base_path)
        os.chmod(base_path, 0o777)

        return base_path


def format_output_result(result: CompilerTaskResult,
                         gateway_client: WebClient):
    parse_out = ""

    if result.php_process_result:
        parse_out += result.php_process_result.out

    if result.perl_process_result:
        parse_out += result.perl_process_result.out

    if result.upload_result:
        parse_out += result.upload_result.out

    if result.compile_result:
        parse_out += result.compile_result.out

    if result.update_result:
        parse_out += result.update_result.out

    if result.restart_result:
        parse_out += result.restart_result.out

    riched_out = EngineOutput()
    if parse_out:
        out = parse_engine_output(parse_out)
        riched_out = load_client_data(gateway_client, out)

    if result.exc_result is not None:
        parse_out += 'ERROR: ' + str(result.exc_result.error)

    success = (result.compile_result
               and result.compile_result.code == 0
               and not len(riched_out.messages)) or False

    output_result = {
        "output": parse_out,
        "messages": [m.to_dict() for m in riched_out.messages],
        "success": success,
        "_run": {
            "p0": result.php_process_result.to_dict()  # noqa
                if result.php_process_result else {},
            "p1": result.perl_process_result.to_dict()
                if result.perl_process_result else {},
            "p2": result.compile_result.to_dict()
                if result.compile_result else {},
            "host": result.host,
            "path": result.engine_complect.remote_path
                if result.engine_complect else "",
            "exc_error": str(result.exc_result.error)
                if result.exc_result else "",
            "exc_traceback": result.exc_result.traceback
                if result.exc_result else "",
        }
    }

    return output_result


def create_complect_revision(*, remote_path, compiler_host, complect_id):
    """
    Creates complect revision from parameters
    :param remote_path:
    :param compiler_host:
    :param complect_id:
    :return:
    """
    rpc = ComplectRevisionRpc(
        tracer=Tracer("compilation"),
        create_session=create_engine(),
    )

    binary_path = Path(remote_path) / "dldata.ie2"
    # Set host codename where we store binary data and it's path
    binary_full_path = "%s:%s" % (compiler_host, binary_path)

    complect_revision = rpc._create(
        complect_id=complect_id,
        binary_path=str(binary_full_path),
        source_archive_path="",
        meta={},
    )

    return {
        "complect_revision_id": complect_revision["id"],
        "complect_revision_code": complect_revision["code"],
    }
