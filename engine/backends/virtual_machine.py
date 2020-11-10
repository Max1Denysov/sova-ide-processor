from pathlib import Path

from engine.backend import (ComplectRemotePath, EngineCompileResult,
                            EngineRestartResult, EngineUpdateResult,
                            EngineUploadResult)
from engine.backends.ssh import SshBackendMixin


class VirtualMachineBackend(SshBackendMixin):
    """
    Dedicated virtual machine backend
    """

    def upload(self, base_path: Path) -> EngineUploadResult:
        return self._upload(base_path)

    def compile(self, complect: ComplectRemotePath) -> EngineCompileResult:
        return self._compile(complect.remote_path)

    def update(self, complect: ComplectRemotePath) \
            -> EngineUpdateResult:
        return self._update(complect.remote_path)

    def restart(self) -> EngineRestartResult:
        return self._restart()
