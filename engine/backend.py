from abc import ABC, abstractmethod
from pathlib import Path


class ComplectRemotePath:
    """
    Complect remote host information.
    remote_path: path in system volume
    docker_path: internal path in docker container
    """
    def __init__(self, remote_path, docker_path):
        self.remote_path = remote_path
        self.docker_path = docker_path


class CallExecutionResult:
    """
    Result of runned process
    """
    def __init__(self, *, code, out, err):
        self.code: int = code
        self.out: str = out
        self.err: str = err

    def to_dict(self):
        return {
            "code": self.code,
            "out": self.out,
            "err": self.err,
        }


class CompileProcessOutput(CallExecutionResult):
    """ Compile process output """
    pass


class DeployProcessOutput:
    """ Deploy process output """

    def __init__(self, *, update_out, restart_out):
        self.update_out: str = update_out
        self.restart_out: str = restart_out

    def to_dict(self):
        return {
            "update_out": self.update_out,
            "restart_out": self.restart_out,
        }


class EngineDownloadResult:
    """
    Download result of DL templates and dictionaries
    """
    def __init__(self, base_path: Path, result: CallExecutionResult):
        self.base_path = base_path
        self.result = result


class EnginePreprocessResult:
    """
    Preprocess DL templates and dictionaries result
    """
    def __init__(self, result: CallExecutionResult):
        self.result = result


class EngineUploadResult:
    """
    Upload preprocessed sources to compiler result
    """
    def __init__(self, complect_path: ComplectRemotePath,
                 result: CallExecutionResult):
        self.complect_path = complect_path
        self.result = result


class EngineCompileResult:
    """
    Compile uploaded sources result
    """
    def __init__(self, result: CallExecutionResult):
        self.result = result


class EngineUpdateResult:
    """
    Update infengine result
    """
    def __init__(self, result: CallExecutionResult):
        self.result = result


class EngineRestartResult:
    """
    Restart infoserver result
    """
    def __init__(self, result: CallExecutionResult):
        self.result = result


class EngineBackend(ABC):
    """
    Backend engine templates handling abstract layer.
    """
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def upload(self, base_path: Path) \
            -> EngineUploadResult:
        """
        Upload path or file

        :param base_path: base path (under root_dir) for templates where
        also stored dl.lst
        :return: result and path where data stored
        """
        pass

    @abstractmethod
    def compile(self,
                complect_path: ComplectRemotePath) -> EngineCompileResult:
        """
        Compiles data in compiler

        :param complect_path:
        :return:
        """
        pass

    @abstractmethod
    def update(self, complect_path: ComplectRemotePath) \
            -> EngineUpdateResult:
        """
        Update server by directory soruce path or binary dldata

        :param complect_path:
        :return:
        """
        pass

    @abstractmethod
    def restart(self) -> EngineRestartResult:
        """
        Restarts infengine
        :return:
        """
        pass

    @abstractmethod
    def get_file(self, remotepath, localpath):
        """
        Download single file to path. Needs paths to file in both params
        """
        pass
