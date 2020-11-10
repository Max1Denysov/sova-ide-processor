import glob
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from engine.backend import EngineDownloadResult, \
    EnginePreprocessResult, CallExecutionResult
from engine.preprocessors.arm1.dictionaries import DictionariesList
from engine.preprocessors.arm1.vars import VarsExport
from engine.preprocessors.arm1.template import extract_template_vars, \
    extract_content_dicts
from engine.preprocessor import Preprocessor

logger = logging.getLogger(__name__)


class Arm1Preprocessor(Preprocessor):
    def __init__(self, gateway_client):
        self.gateway_client = gateway_client

    def download(self, root_dir: Path, complect_id: Optional[str] = None) \
            -> EngineDownloadResult:
        logger.debug("Started downloading")
        php_process_result = self._run_php_preprocessor(
            complect_id=complect_id,
            root_dir=root_dir,
        )

        if php_process_result.code != 0:
            # Return root dir, will fail
            return EngineDownloadResult(root_dir, result=php_process_result)

        source_dir = self._get_php_source_dir(root_dir)
        logger.debug("Finished downloading")
        return EngineDownloadResult(source_dir, result=php_process_result)

    def preprocess(self, base_path: Path) \
            -> EnginePreprocessResult:
        logger.debug("Started preprocessing")
        perl_process_result = self._run_perl_preprocessor(base_path)

        if "ERROR" not in perl_process_result.out:
            logger.debug("Started processing templates")
            used_dicts = self._process_templates_and_vars(base_path)
            logger.debug("Finished processing templates")

            dict_export = DictionariesList(base_path=base_path)
            dict_export.export(
                common_dicts=True,
                used_dicts=used_dicts,
                dictionary_rpc=self.gateway_client.component("dictionary"),
            )

        logger.debug("Finished preprocessing")

        return EnginePreprocessResult(perl_process_result)

    def _get_php_source_dir(self, base_path: Path) -> Path:
        """
        Peek source dir after php preprocessor
        :param base_path:
        :return:
        """
        child_dir = list(it for it in (base_path / "source_new").iterdir()
                         if it.is_dir())
        if len(child_dir) != 1:
            logger.error("More than one directory in result!")

        return child_dir[0]

    def _run_php_preprocessor(self, complect_id: str, root_dir: Path) \
            -> CallExecutionResult:
        result = self._run_subprocess([
            "tools/cli.phar", "prepare",
            "--uri", self.gateway_client.url,
            "--complect", complect_id,
            "--destination", str(root_dir),
        ])

        return result

    def _run_perl_preprocessor(self, complect_path: Path) \
            -> CallExecutionResult:
        result = self._run_subprocess([
            "tools/DLPreProcessor.pl", str(complect_path),
        ])

        return result

    def _run_subprocess(self, cmd) -> CallExecutionResult:
        logger.info("Running: %s", cmd)

        with tempfile.TemporaryFile() as fout:
            with tempfile.TemporaryFile() as ferr:
                result = subprocess.run(cmd, stdout=fout, stderr=ferr)
                code = result.returncode

                fout.seek(0)
                out = fout.read().decode(errors='replace')

                ferr.seek(0)
                err = ferr.read().decode(errors='replace')

        logger.info("Result: %d. Out: %s. Err: %s", code, out, err)

        return CallExecutionResult(code=code, out=out, err=err)

    def _process_templates_and_vars(self, source_dir: Path):
        """
        Read templates for dictionary and var references.
        Really we patch defvars file after php init creation.
        Library vars of suites enabling switched on to "1".
        All other vars set to "".

        :param source_dir: Source root of preprocessed data
        :return:
        """

        logger.debug("Started looking templates")
        template_files = glob.glob(
            str(source_dir / "**/inf_base.templates"), recursive=True)
        logger.debug("Finished looking templates: %s", template_files)

        vars_export = VarsExport(source_dir)

        used_dicts = set()
        for template_file in template_files:
            logger.debug("Started processing: %s", template_file)
            with open(template_file) as f:
                logger.debug("  Started reading file")
                data = f.read()
                logger.debug("  Finished reading file")

                vars = extract_template_vars(data)
                logger.debug("  Extracted vars")
                lib_vars = set(v for v in vars if v.startswith("LIB_"))
                if lib_vars:
                    vars_export.add_vars(lib_vars, "1")

                other_vars = vars - lib_vars
                if other_vars:
                    vars_export.add_vars(other_vars, "")

                d = extract_content_dicts(data)
                logger.debug("  Extracted dicts")
                if d:
                    used_dicts.update(set([q.lower() for q in d]))

            logger.debug("Finished processing: %s", template_file)

        logger.debug("Started vars export")
        vars_export.export()
        logger.debug("Finished vars export")

        return used_dicts
