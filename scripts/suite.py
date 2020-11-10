import os
import re
import tempfile

from nlab.archiver import Archiver
from settings import GATEWAY_URL, HEADERS
from utils import file_to_uint_8_array, post_request, uint_8_array_to_file


class ImportSuite:
    """
    Класс для получения шаблонов из архива
    """
    def __init__(self):
        self._archiver = Archiver()

    @staticmethod
    def _read_files(path_to_directory):
        """
        Обход файлов архива
        """
        for dir_path, _, file_names in os.walk(path_to_directory):
            for file in file_names:
                with open(os.path.join(dir_path, file)) as f:
                    yield file, f.read()

    def process(self, filepath):
        """
        Разбиение на шаблоны
        """
        with tempfile.TemporaryDirectory() as path:
            self._archiver.extractall(filepath, path)
            for _, file in self._read_files(path):
                # разбиваем по двум пустым строкам
                templates = re.split(r'\n\s*\n\s*\n', file)
                for template in templates:
                    yield template
                yield None  # означает, что переходим к следующему файлу


def create_suite_request_data(profile_id, title=None, state="active",
                              is_enabled=True):
    """
    Формирование запроса на создание набора
    """
    return {
        "jsonrpc": "2.0",
        "method": "suite.create",
        "params": {
            "title": title,
            "state": state,
            "profile_id": profile_id,
            "is_enabled": is_enabled,
        },
        "id": 1,
    }


def create_template_request_data(suite_id, content, is_enabled=True,
                                 meta=None):
    """
    Формирование запроса на создание шаблона
    """
    return {
            "jsonrpc": "2.0",
            "method": "template.create",
            "params": {
                "content": content,
                "suite_id": suite_id,
                "is_enabled": is_enabled,
                "meta": meta,
            },
            "id": 1,
        }


def import_run(profile_id, file_name, data):
    """
    Запуск импорта шаблонов
    """
    with tempfile.TemporaryDirectory() as temp_path:
        uint_8_array_to_file(os.path.join(temp_path, file_name), data)

        suites = ImportSuite()

        suite_id = None
        prev_template = None

        for template in suites.process(os.path.join(temp_path, file_name)):
            if prev_template is None and template:  # открыли новый файл
                request_data = create_suite_request_data(profile_id=profile_id)
                response = post_request(
                    url=GATEWAY_URL, headers=HEADERS,
                    request_data=request_data
                )
                suite_id = response["result"]["response"]["id"]

            prev_template = template
            if not template:
                continue

            request_data = create_template_request_data(
                suite_id=suite_id, content=template
            )

            post_request(
                url=GATEWAY_URL, headers=HEADERS, request_data=request_data
            )


def export_run(suites):
    """
    Запуск экспорта шаблонов

    Формат входных данных:

    suites = {"uid1": {"name": "test",
                       "templates": ["текст", "текст", "текст"]},
              "uid2": {"name": "test",
                       "templates": ["текст", "текст", "текст"]}
              }
    """
    with tempfile.TemporaryDirectory() as temp_path:
        for _, value in suites.items():
            file_name = value["name"]
            postfix = 1
            # проверяем файлы
            while os.path.isfile(os.path.join(temp_path, f"{file_name}.txt")):
                file_name = f'{value["name"]}_{postfix}'
                postfix += 1
            # создаем файлы
            with open(os.path.join(temp_path, f"{file_name}.txt"), "w") as f:
                for template in value["templates"]:
                    f.write(template)
                    f.write("\n\n\n")
        # архивируем файлы
        archiver = Archiver()
        archive_name = "result.zip"
        archiver.compress(
            folderpath=temp_path, path=temp_path, archive_name=archive_name
        )

        return file_to_uint_8_array(os.path.join(temp_path, archive_name))
