from abc import abstractmethod
from pathlib import Path
from typing import Optional

from engine.backend import EngineDownloadResult, EnginePreprocessResult


class Preprocessor:
    @abstractmethod
    def download(self, root_dir: Path,
                 complect_id: Optional[str] = None) -> EngineDownloadResult:
        """
        Download DL templates and soirce

        :param root_dir: dir where to place files
        :param complect_id: complect identifier
        :return:
        """
        pass

    @abstractmethod
    def preprocess(self, base_path: Path) \
            -> EnginePreprocessResult:
        """
        Preprocess data

        :param base_path: base path (under root_dir) for templates where
        also stored dl.lst
        :return:
        """
        pass
