from urllib.parse import urljoin

import requests
from nlab.rpc import ApiError
from settings import (HEADERS, NLAB_ARM_ENGINE_SERVICE_HOST,
                      NLAB_ARM_TEST_TESTCASE_INF_NAME, SESSION_ID)


def init_session(inf_id, inf_name, session_id):
    """
    Инициализация сессии
    """
    params = {
        "inf_id": inf_id,
        "session_id": session_id,
        "inf_name": inf_name,
    }

    try:
        result = requests.post(
            url=urljoin(NLAB_ARM_ENGINE_SERVICE_HOST, "init_session"),
            params=params,
            headers=HEADERS
        )
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError,
            requests.exceptions.Timeout, requests.exceptions.RequestException):

        raise ApiError(
            code="INF_ENGINE_ERROR",
            message="Inf engine session initialization error."
        )

    return result.json()["status"]


def send_request(inf_id, session_id):
    """
    Получение ответа на реплику
    """

    def inner(replica):
        params = {
            "inf_id": inf_id,
            "session_id": session_id,
            "replica": replica,
        }

        try:
            req = requests.post(
                url=urljoin(NLAB_ARM_ENGINE_SERVICE_HOST, "send_request"),
                params=params,
                headers=HEADERS
            )
        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException):

            raise ApiError(
                code="INF_ENGINE_ERROR",
                message="Inf engine session initialization error."
            )

        req = req.json()

        if req["status"]:
            return req["data"]["text"]

        return None

    return inner


def run(ids, testcases, profile_info):
    """
    Запуск тесткейсов
    """
    result = []

    inf_id = profile_info["engine_id"]
    if not inf_id:
        raise ApiError(
            code="INF_ENGINE_ERROR", message="Inf engine_id is null."
        )

    inf_name = profile_info["code"] or NLAB_ARM_TEST_TESTCASE_INF_NAME

    if not init_session(inf_id=inf_id, inf_name=inf_name,
                        session_id=SESSION_ID):
        raise ApiError(
            code="INF_ENGINE_ERROR",
            message="Inf engine session initialization error."
        )

    send_replica_request = send_request(inf_id=inf_id, session_id=SESSION_ID)

    testcases_dict = {}

    for tc in testcases:
        testcases_dict[tc["id"]] = tc

    for id in ids:
        item = {"id": id, "dialogue": []}

        try:
            testcase = testcases_dict[id]

        except KeyError:
            item["error"] = {
                "message": "Can't find testcase with id=%r" % id,
                "code": "NOT_EXISTS"
            }
            result.append(item)
            continue

        for replica in testcase["replicas"]:
            response = send_replica_request(replica)
            item["dialogue"].append({"request": replica, "response": response})

        result.append(item)

    return {"dialogues": result}
