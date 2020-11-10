import argparse
import os
import traceback
from pathlib import Path
from typing import List

from engine.preprocessors.arm1.dictionaries import process_raw_text
from nlab.rpc.client import WebClient


def _upload_dict(name, text, is_common, profile_ids, dictionary_rpc):

    try:
        have_dicts = dictionary_rpc.list(
            code=name,
        )
        if have_dicts["total"]:
            print("U", name)
            d = dictionary_rpc.update(
                id=have_dicts["items"][0]["id"],
                content=text,
                common=is_common,
                hidden=False,
                profile_ids=profile_ids if not is_common else []
            )
        else:
            print("C", name)
            d = dictionary_rpc.create(  # noqa
                code=name,
                content=text,
                common=is_common,
                hidden=False,
                profile_ids=profile_ids if not is_common else []
            )
    except KeyboardInterrupt:
        exit(-1)

    except Exception:
        print(traceback.format_exc())


def get_file_names(folder_name: str, extension: str) -> List[Path]:
    """ Возвращает список полных имен файлов с расширением extension
        в папке folder_name.

        Если папки нет - поднимается исключение.
        Если файлов с нужным типом в папке нет - поднимается исключение.
    """
    path = Path(folder_name)

    file_names = [
        path/file_name for file_name in os.listdir(folder_name)
        if file_name.endswith(f'.{extension}')
    ]

    if not file_names:
        raise FileNotFoundError(
            f"There are no '{extension}' files in the "
            f"'{path}' folder!"
        )

    return file_names


def process_inf_dicts(*, dictionary_path, profile_name, client):

    dictionary_rpc = client.component("dictionary")
    profile_id = None

    if profile_name is not None:
        # Получим profile_id
        profile_rpc = client.component("profile")
        profiles = profile_rpc.list()

        for profile in profiles['items']:
            if profile['name'] == profile_name:
                profile_id = profile['id']
                break
        if profile_id is None:
            raise Exception(
                "Profile with the name '{profile_name}' not found!"
            )

    is_common = True if profile_id is None else False
    profile_ids = [] if profile_id is None else [profile_id, ]

    # Получим все полные имена файлов со словарями из папки dictionary_path
    file_names = get_file_names(dictionary_path, 'txt')

    for file_name in file_names:

        with open(file_name) as f:
            dict_text = process_raw_text(f.read())
            dict_name = file_name.stem

        _upload_dict(
            name=dict_name,
            text=dict_text,
            is_common=is_common,
            profile_ids=profile_ids,
            dictionary_rpc=dictionary_rpc,
        )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')

    parser.add_argument('path', help='Dictionaries path')

    help_arg = 'Target ARM gateway host e.g. '
    help_arg += '"http://host.name/template"'
    parser.add_argument('-t', '--target', required=True, help=help_arg)

    parser.add_argument('--profile-name', help='Profile name')

    args = parser.parse_args()

    process_inf_dicts(
        dictionary_path=args.path,
        profile_name=args.profile_name,  # Если не указан, то будет None
        client=WebClient(url=args.target),
    )
