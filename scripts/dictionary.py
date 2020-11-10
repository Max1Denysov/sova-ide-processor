import os
import tempfile

from engine.preprocessors.arm1 import _process_filename
from nlab.archiver import Archiver
from settings import GATEWAY_URL, HEADERS
from utils import file_to_uint_8_array, post_request, uint_8_array_to_file


class ImportDictionary:
    """
    Класс для получения словарей из архива
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
        Разбиение на словари
        """
        with tempfile.TemporaryDirectory() as path:
            self._archiver.extractall(filepath, path)
            for file_name, file in self._read_files(path):
                yield file_name, file


def create_dictionary_request_data(profile_id, code, description, content,
                                   state="active", common=False,
                                   is_enabled=True):
    """
    Формирование запроса на создание словаря
    """
    return {
            "jsonrpc": "2.0",
            "method": "dictionary.create",
            "params": {
                "code": code,
                "description": description,
                "content": content,
                "state": state,
                "common": common,
                "meta": {},
                "profile_ids": [profile_id] if profile_id else [],
                "is_enabled": is_enabled,
            },
            "id": 1,
        }


def import_run(profile_id, file_name, data):
    """
    Запуск импорта словарей
    """
    with tempfile.TemporaryDirectory() as temp_path:
        uint_8_array_to_file(os.path.join(temp_path, file_name), data)

        dictionaries = ImportDictionary()

        for file_name, dictionary in dictionaries.process(
            os.path.join(temp_path, file_name)
        ):
            request_data = create_dictionary_request_data(
                profile_id=profile_id,
                code=os.path.splitext(_process_filename(file_name))[0],
                description=file_name,
                content=dictionary
            )
            post_request(
                url=GATEWAY_URL,
                headers=HEADERS,
                request_data=request_data
            )


def export_run(dictionaries):
    """
    Запуск экспорта словарей

    Формат входных данных:

    dictionaries = {"uid1": {"name": "test",
                             "content": "текст"},
                    "uid2": {"name": "test",
                             "content": "текст"}
                    }
    """
    with tempfile.TemporaryDirectory() as temp_path:
        for _, value in dictionaries.items():
            file_name = value["name"]
            postfix = 1
            # проверяем файлы
            while os.path.isfile(os.path.join(temp_path, f"{file_name}.txt")):
                file_name = f'{value["name"]}_{postfix}'
                postfix += 1
            # создаем файлы
            with open(os.path.join(temp_path, f"{file_name}.txt"), "w") as f:
                f.write(value["content"])
        # архивируем файлы
        archiver = Archiver()
        archive_name = "result.zip"
        archiver.compress(
            folderpath=temp_path, path=temp_path, archive_name=archive_name
        )

        return file_to_uint_8_array(os.path.join(temp_path, archive_name))
