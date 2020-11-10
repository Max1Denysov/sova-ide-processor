from pathlib import Path
from typing import Optional

from engine.backend import (CallExecutionResult, EngineDownloadResult,
                            EnginePreprocessResult)
from engine.preprocessor import Preprocessor


class DummyPreprocessor(Preprocessor):
    """
    Dummy preprocessor with successful operations result
    """

    def __init__(self):
        pass

    def download(self, root_dir: Path,
                 complect_id: Optional[str] = None) -> EngineDownloadResult:
        base_path = Path('.')
        ok_result = CallExecutionResult(code=0, out="", err="")
        return EngineDownloadResult(base_path, ok_result)

    def preprocess(self, base_path: Path) -> EnginePreprocessResult:
        ok_result = CallExecutionResult(code=0, out="", err="")
        return EnginePreprocessResult(ok_result)
