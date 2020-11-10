import json

from flask import Response


def make_json_response(content):
    """
    Создает flask - ответ с содержимым JSON

    :param content: содержимое (str или dict)
    :return: Response
    """
    if isinstance(content, str):
        resp = Response(content)
    elif isinstance(content, dict):
        resp = Response(json.dumps(content))
    else:
        raise Exception('make_json_response get wrong type of content')

    resp.headers['Content-Type'] = 'application/json'
    return resp
