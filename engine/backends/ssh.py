import logging
import os
from abc import ABC
from io import StringIO
from pathlib import Path
from stat import S_ISDIR

import paramiko
from engine.backend import (CallExecutionResult, ComplectRemotePath,
                            EngineBackend, EngineCompileResult,
                            EngineRestartResult, EngineUpdateResult,
                            EngineUploadResult)
from engine.util import generate_mktemp_pattern
from paramiko import SFTPClient

logger = logging.getLogger(__name__)


class SshBackendMixin(EngineBackend, ABC):
    """
    Common code for ssh
    """
    strict_mode = True

    def __init__(self, *, target, user, host, engine_path, data_path,
                 private_key):

        self.target = target
        self.client = None
        self.user = user
        self.host = host
        self.engine_path = Path(engine_path)
        self.private_key = private_key
        self.data_path = data_path

        self._sftp = None

    def connect(self):
        return self._connect()

    def close(self):
        return self._close()

    def get_file(self, remotepath, localpath):
        """
            Download single file to path. Needs paths to file in both params
        """
        return self._get_file(remotepath, localpath)

    def _connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

        logger.info(
            "Connecting to {username}@{hostname} with private key".format(
                hostname=self.host,
                username=self.user,
            ))

        pkey = paramiko.RSAKey.from_private_key(StringIO(self.private_key))
        self.client.connect(
            hostname=self.host,
            username=self.user,
            pkey=pkey
        )

        logger.info("Connected")

        self._sftp = SFTPClient.from_transport(self.client.get_transport())

    def _close(self):
        self.client.close()

    def _upload(self, local_path: Path,
                arch_file_name: str = 'arch_source_1q2w3e4r5t.tgz'
                ) -> EngineUploadResult:
        """
            Загружает комплект на сервер и возвращает объект для работы с ним
        """
        remote_path = self._mktemp()

        if local_path.is_dir():

            # 1. Сжать содержимое local_path в один файл
            # 1.1. Собираем команду:
            # ... перейдем в папку с данными
            cmd_arch = 'cd %s' % local_path
            # ... создадим архив
            cmd_arch += ' && tar -czvf %s * > /dev/null' % arch_file_name
            # 1.2. Выполним команду:
            os.system(cmd_arch)

            # 2. Загрузка архива на удаленный сервер
            self._put_file(
                Path(local_path)/arch_file_name,
                Path(remote_path)/arch_file_name
            )

            # 3. На удаленном сервере извлечем все из архива в remote_path
            # и удалим файл с архивом
            # 3.1. Собираем команду:
            # ... перейдем в папку с архивом
            cmd_unzip = 'cd %s' % remote_path
            # ... распакуем архив
            cmd_unzip += ' && tar -xzvf %s' % arch_file_name
            # ... удалим файл с архивом
            cmd_unzip += ' && rm %s' % arch_file_name
            # 3.2. Выполним команду на удаленном сервере:
            stdin, stdout, stderr = self.client.exec_command(cmd_unzip)

            exit_code = stdout.channel.recv_exit_status()
            err = stderr.read().decode("utf-8")
            logger.info(
                f'_upload - Uploaded remote cmd: "{cmd_unzip}". '
                f'Got - exit_code: {exit_code}, err: "{err}".'
            )

        else:
            self._put_file(Path(local_path), Path(remote_path))

        # Удалим файлы и папки старше недели на удаленном диске
        # (для освобождения места)
        archive_folder_path = Path(remote_path).parent
        cmd_delete = 'find %s -mtime +%s -delete' % (archive_folder_path, 7)
        stdin, stdout, stderr = self.client.exec_command(cmd_delete)
        exit_code = stdout.channel.recv_exit_status()
        err = stderr.read().decode("utf-8")
        logger.info(
            f'_upload - *Deleted* remote arch, cmd: "{cmd_delete}". '
            f'Got - exit_code: {exit_code}, err: "{err}".'
        )

        docker_path = Path("/root/volume") / Path(remote_path).relative_to(
            self.data_path)

        complect = ComplectRemotePath(remote_path=remote_path,
                                      docker_path=str(docker_path))
        upload_result = CallExecutionResult(code=0, out="", err="")  # TODO

        return EngineUploadResult(complect, result=upload_result)

    def _execute(self, *args, **kwargs) -> CallExecutionResult:
        """
        Execute remote process

        :param args:
        :param kwargs:
        :return:
        """
        logger.info(f"Running: {args}, kwargs: {kwargs}")
        stdin, stdout, stderr = self.client.exec_command(*args, **kwargs)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8")
        err = stderr.read().decode("utf-8")
        logger.info(
            f"Executed: {args}, kwargs: {kwargs}. "
            f"Got: code: {exit_code}, out: {out}, err: {err}"
        )

        return CallExecutionResult(code=exit_code, out=out, err=err)

    def _check_execute(self, *args, **kwargs) -> CallExecutionResult:
        """
        Execute process with ensuring 0 code result

        :param args:
        :param kwargs:
        :return:
        """
        result = self._execute(*args, **kwargs)
        if result.code != 0:
            raise RuntimeError(
                "Non-null exit code {exit_code} with args: {args}, kwargs: "
                "{kwargs}, stdout: {out}, "
                "stderr: {err}".format(
                    exit_code=result.code, args=args, kwargs=kwargs,
                    out=result.out, err=result.err
                )
            )

        return result

    def _compile(self, complect_path: Path) -> EngineCompileResult:
        """ Compiles data by path """
        cmd = [
            "cd " + str(complect_path) + " &&",
            str(self.engine_path / "bin/InfCompiler"),
            str(self.engine_path / "conf/InfCompiler.conf"),
            "--dldata-root", ".",
            "--strict", "false",
        ]

        cmd_str = " ".join(cmd)
        result = self._execute(cmd_str)

        return EngineCompileResult(result)

    def _update(self, complect_path: Path) -> EngineUpdateResult:
        result = self._execute(
            "InfEngineManager.pl --dl-update %s --verbose" %
            (Path(complect_path) / "dldata.ie2",)
        )

        return EngineUpdateResult(result)

    def _restart(self) -> EngineRestartResult:
        result = self._execute("InfEngineControl.pl --restart")
        return EngineRestartResult(result)

    def _put_dir(self, source: Path, dest: Path):
        for root, dirs, files in os.walk(source):
            relative_root = Path(root).relative_to(source)

            for dir in dirs:
                out = dest / relative_root / dir
                logger.debug(f"Mkdir: {out}")
                try:
                    self._sftp.mkdir(str(out))
                except OSError as e:
                    logger.error(f"Mkdir result: may be ok if directory is "
                                 f"already created: {e}")

            for file in files:
                from_f = Path(root) / file
                dest_d = dest / relative_root / file
                logger.debug(f"Copy: {from_f} -> {dest_d}")
                self._sftp.put(str(from_f), str(dest_d))

    def _sftp_walk(self, remotepath):
        remotepath = remotepath
        path = remotepath
        files = []
        folders = []
        for f in self._sftp.listdir_attr(remotepath):
            if S_ISDIR(f.st_mode):
                folders.append(f.filename)
            else:
                files.append(f.filename)
        logger.debug(f"Walk: {path}, {folders}, {files}")
        yield path, folders, files
        for folder in folders:
            new_path = os.path.join(remotepath, folder)
            for x in self._sftp_walk(new_path):
                yield x

    def _get_all(self, remotepath, localpath):
        """ Download all from remote path """
        remotepath = remotepath
        self._sftp.chdir(os.path.split(remotepath)[0])
        parent = os.path.split(remotepath)[1]

        try:
            os.mkdir(localpath)
        except Exception:
            pass

        for walker in self._sftp_walk(parent):
            try:
                os.mkdir(os.path.join(localpath, walker[0]))
            except Exception:
                pass
            for file in walker[2]:
                self._sftp.get(os.path.join(walker[0], file),
                               os.path.join(localpath, walker[0], file))

    def _get_file(self, remotepath, localpath):
        """
            Download single file to path. Needs paths to file in both params
        """
        logger.info(f"Get file {remotepath} -> {localpath}")
        self._sftp.get(str(remotepath), str(localpath))

    def _put_file(self, localpath, remotepath):
        """ Put single file to path. Needs paths to file in both params """
        logger.info(f"Put file {localpath} -> {remotepath}")
        self._sftp.put(str(localpath), str(remotepath))

    def _mktemp(self):
        """
        Creates temporary directory in data path with given pattern
        :return: new directory
        """
        mktemp_pattern = generate_mktemp_pattern()
        result = self._check_execute(
            f"mktemp -d -t {mktemp_pattern} -p {self.data_path}")
        remote_path = result.out.rstrip()
        return remote_path

    def _get_scp_path(self, complect: ComplectRemotePath):
        return f"{self.user}@{self.host}:{complect.remote_path}"
