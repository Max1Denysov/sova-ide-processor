from pathlib import Path

from engine.backend import (CallExecutionResult, ComplectRemotePath,
                            EngineBackend, EngineCompileResult,
                            EngineRestartResult, EngineUpdateResult,
                            EngineUploadResult)


class DummyBackend(EngineBackend):
    """
    Dummy backend with successful operations result
    """

    def __init__(self):
        pass

    def upload(self, base_path: Path) -> EngineUploadResult:
        ok_result = CallExecutionResult(code=0, out="", err="")
        complect_path = ComplectRemotePath("", "")
        return EngineUploadResult(
            complect_path=complect_path, result=ok_result
        )

    def compile(self,
                complect_path: ComplectRemotePath) -> EngineCompileResult:
        ok_result = CallExecutionResult(code=0, out="", err="")
        return EngineCompileResult(result=ok_result)

    def update(self, complect_path: ComplectRemotePath) \
            -> EngineUpdateResult:
        ok_result = CallExecutionResult(code=0, out="", err="")
        return EngineUpdateResult(result=ok_result)

    def restart(self) -> EngineRestartResult:
        ok_result = CallExecutionResult(code=0, out="", err="")
        return EngineRestartResult(result=ok_result)

    def connect(self):
        pass

    def close(self):
        pass

    def get_file(self, remotepath, localpath):
        pass
