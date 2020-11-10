import requests
from nlab.rpc.exceptions import ApiError


def post_request(url, headers, request_data):
    """
    Выполнение POST запроса
    """
    try:
        res = requests.post(url, json=request_data, headers=headers)
    except requests.exceptions.HTTPError as errh:
        raise ApiError(code="PROCESSOR_HTTP_ERROR", message=errh)
    except requests.exceptions.ConnectionError as errc:
        raise ApiError(code="PROCESSOR_CONNECTING_ERROR", message=errc)
    except requests.exceptions.Timeout as errt:
        raise ApiError(code="PROCESSOR_TIMEOUT_ERROR", message=errt)
    except requests.exceptions.RequestException as err:
        raise ApiError(code="PROCESSOR_REQUEST_ERROR", message=err)

    return res.json()


def get_create_request(method, script, type, extra=None, args=None):
    """
    Формирование запроса на создание задачи
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": {
            "script": script,
            "type": type,
            "extra": extra,
            "args": args
        },
        "id": 1,
    }


def get_info_request(method, **kwargs):
    """
    Формирование запроса на получение информации по задаче
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": kwargs,
        "id": 1,
    }
