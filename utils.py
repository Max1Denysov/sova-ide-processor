import numpy as np
import requests


def post_request(url, request_data, headers):
    """
    Выполнение POST запроса
    """
    try:
        res = requests.post(url, json=request_data, headers=headers)
    except requests.exceptions.HTTPError as errh:
        raise Exception("Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        raise Exception("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        raise Exception("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        raise Exception("Oops: Something Else", err)

    return res.json()


def file_to_uint_8_array(path):
    """Конвертирование файла в формат Uint8Array"""
    with open(path) as f:
        header = np.fromfile(f, dtype='uint8')
        return header.tolist()


def uint_8_array_to_file(path, array):
    """Конвертирование Uint8Array в файл"""
    with open(path, "wb") as f:
        f.write(bytearray(array))


class TaskResult:
    def __init__(self, result, extra=None):
        self.result = result
        self.extra = extra
