from collections import namedtuple
from enum import Enum
from typing import Optional


class EngineTaskType(Enum):
    COMPILE = 1
    DEPLOY = 2


class EngineTask:
    """
    Task for engine
    """
    def __init__(self, task_type: EngineTaskType, target: str):
        """
        :param task_type:
        :param target: compiler/deployer unit target
        """
        self.task_type = task_type
        self.target = target


class EngineTaskResult:
    """
    Task response
    """
    def __init__(self, task_type: EngineTaskType):
        """
        :param task_type:
        """
        self.task_type = task_type


class CompilerTask(EngineTask):
    """
    Task for compilation templates
    """
    def __init__(self, *,
                 target: str,
                 complect_id: str,
                 compiler_host: str,
                 task_id: Optional[int],
                 try_create_revision: bool,
                 do_upload: bool,
                 do_compile: bool,
                 do_update: bool,
                 strict: bool):
        """
        :param target: compiler unit target
        :param complect_id: complect to compile
        :param compiler_host:
        :param task_id: task id
        :param try_create_revision:
        :param do_compile: compile or not on
        :param do_update: update compiler node or not
        :param strict: mode for compilation mode
        """

        super().__init__(EngineTaskType.COMPILE, target=target)

        self.complect_id = complect_id
        self.compiler_host = compiler_host
        self.task_id = task_id
        self.try_create_revision = try_create_revision
        self.do_upload = do_upload
        self.do_compile = do_compile
        self.do_update = do_update
        self.strict = strict


ErrorWithTraceback = namedtuple('ErrorWithTraceback', 'error, traceback')


class CompilerTaskResult(EngineTaskResult):
    """
    Compiler task result
    """
    def __init__(self):
        super().__init__(EngineTaskType.COMPILE)

        self.php_process_result = None
        self.perl_process_result = None
        self.upload_result = None
        self.compile_result = None
        self.update_result = None
        self.restart_result = None
        self.exc_result: Optional[ErrorWithTraceback] = None
        self.engine_complect = None
        self.host = None


class DeployTask(EngineTask):
    """
    Deploy complect revision
    """
    def __init__(self, *,
                 complect_revision_id: str,
                 target: str
                 ):
        """
        :param complect_revision_id: deploy revision id
        :param target:
        """

        super().__init__(EngineTaskType.COMPILE, target=target)

        self.complect_revision_id = complect_revision_id
        self.target = target


class DeployTaskResult(EngineTaskResult):
    """
    Deploy task result
    """
    def __init__(self):
        super().__init__(EngineTaskType.DEPLOY)

        self.success = False
        self.output = ""
        self.complect_id = ""
