import logging
import subprocess
from pathlib import Path

from engine.backend import (CallExecutionResult, ComplectRemotePath,
                            EngineBackend, EngineCompileResult,
                            EngineRestartResult, EngineUpdateResult,
                            EngineUploadResult)
from engine.util import generate_mktemp_pattern

logger = logging.getLogger(__name__)


class KubernetesBackend(EngineBackend):
    """
    Kubernetes pod call
    """

    def __init__(self, pod_name: str,
                 kube_config_path: str, kube_namespace: str):

        self._engine_path = Path('/usr/local/InfEngine')
        self._upload_path = Path('/tmp/')
        self._strict_mode = False

        self._pod_name = pod_name

        self._kube_config_path = kube_config_path
        self._kube_namespace = kube_namespace

    def connect(self):
        pass

    def close(self):
        pass

    def upload(self, base_path: Path) -> EngineUploadResult:
        cmd = [
            'exec',
            self._pod_name,
            '--',
            'mktemp',
            '-d',
            '-t', generate_mktemp_pattern(),
            '-p', str(self._upload_path),
        ]

        mktemp_result = self._kubectl_execute(cmd)  # noqa

        cmd = [
            'cp',
            str(base_path),  # Local path from
            f'{self._pod_name}:{self._upload_path}',  # Remote pod:path
        ]

        cp_result = self._kubectl_execute(cmd)
        # logger.debug("Started uploading")
        # self.engine_ssh.connect()
        complect_path = ComplectRemotePath(remote_path=base_path,
                                           docker_path=self._upload_path)
        return EngineUploadResult(
            complect_path=complect_path, result=cp_result
        )

    def compile(self, complect: ComplectRemotePath) -> EngineCompileResult:
        """
        Compiles complect
        """

        cmd = [
            'exec',
            str(self._engine_path / 'bin/InfCompiler'),
            str(self._engine_path / 'conf/InfCompiler.conf'),
            '--dldata-root', str(complect.docker_path),
            '--strict', 'true' if self._strict_mode else 'false',
        ]

        result = self._kubectl_execute(cmd)

        return EngineCompileResult(result)

    def update(self, complect_path: ComplectRemotePath) -> EngineUpdateResult:
        pass

    def restart(self) -> EngineRestartResult:
        pass

    def get_file(self, remotepath, localpath):
        pass

    def _kubectl_execute(self, cmd) -> CallExecutionResult:
        env = {}

        if self._kube_config_path is not None:
            env['KUBECONFIG'] = self._kube_config_path

        call_cmd = [
            '/usr/local/bin/kubectl'
        ]

        if self._kube_namespace is not None:
            call_cmd.extend(['--namespace', self._kube_namespace])

        call_cmd.extend(cmd)

        proc = subprocess.run(call_cmd, capture_output=True, env=env)

        out = proc.stdout.decode('utf-8', errors='ignore')
        err = proc.stderr.decode('utf-8', errors='ignore')

        return CallExecutionResult(
            code=proc.returncode,
            out=out,
            err=err,
        )
