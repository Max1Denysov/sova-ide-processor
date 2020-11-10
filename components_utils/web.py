from nlab.rpc.client import WebClient
from settings import GATEWAY_URL


def get_complect_code(complect_id) -> str:
    """
        Возвращает значение поля "code" для "complect_id"
        (при помощи запроса к API-gateway)
    """
    gateway_client = WebClient(url=GATEWAY_URL)
    complects = gateway_client.component("complect")
    complect = complects.fetch(id=complect_id)
    code = complect["code"]

    return code
