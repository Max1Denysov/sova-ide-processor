from pathlib import Path

from engine.backend import (CallExecutionResult, ComplectRemotePath,
                            EngineCompileResult, EngineRestartResult,
                            EngineUpdateResult, EngineUploadResult)
from engine.backends.ssh import SshBackendMixin
from engine.util import generate_mktemp_pattern


class DockerBackend(SshBackendMixin):
    """
    Docker backend
    """
    def __init__(self, *, target, user, host, engine_path, data_path,
                 container_name, private_key):
        super().__init__(
            target=target,
            user=user,
            host=host,
            engine_path=engine_path,
            data_path=data_path,
            private_key=private_key,
        )
        self._container_name = container_name

    def upload(self, base_path: Path) -> EngineUploadResult:
        return self._upload(base_path)

    def compile(self, complect: ComplectRemotePath) -> EngineCompileResult:
        """ Compiles data by path """
        return self._compile(complect.docker_path)

    def update(self, complect: ComplectRemotePath) \
            -> EngineUpdateResult:
        return self._update(complect.docker_path)

    def restart(self) -> EngineRestartResult:
        return self._restart()

    def _execute(self, *args, **kwargs) -> CallExecutionResult:
        if len(args) != 1 and len(kwargs) == 0:
            raise RuntimeError("Only one str parameter supported in _execute!")

        call = f"sudo docker exec {self._get_docker_container()} " \
               f"bash -c '{args[0]}'"
        return super()._execute(call)

    def _mktemp(self):
        """
        Creates temporary directory in data path with given pattern
        :return: new directory
        """
        mktemp_pattern = generate_mktemp_pattern()
        result = super()._execute(
            f"mktemp -d -t {mktemp_pattern} -p {self.data_path}")
        remote_path = result.out.rstrip()
        return remote_path

    def _get_docker_container(self):
        result = super()._execute(
            "sudo docker ps --format '{{.ID}}' --filter "
            "name=" + self._container_name
        )
        if not result.out:
            raise RuntimeError("Can't find container '%s'" %
                               self._container_name)
        docker_container = result.out.rstrip()
        return docker_container
