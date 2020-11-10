import settings
from nlab.rpc import RpcGroup


class ClusterRpc(RpcGroup):
    """Кластер"""
    def __init__(self, tracer, create_session):

        super().__init__(
            name="cluster", tracer=tracer, create_session=create_session
        )

    def list_compilers(self):
        """Получение списка компиляторов"""
        return self._get_from_hosts(settings.ENGINE_COMPILER_HOSTS)

    def list_engines(self):
        """Получение списка движков"""
        return self._get_from_hosts(settings.ENGINE_DEPLOY_HOSTS)

    @staticmethod
    def _get_from_hosts(from_hosts):
        """Получение списка"""
        items = []

        for key, item in from_hosts.items():
            host = item["host"]
            port = item.get("port", 2255)
            items.append({
                "code": key,
                "host": item["host"],
                "infengine_url": f"tcp:{host}:{port}",
            })

        total_items = len(items)

        return {
            "items": items,
            "total": total_items,
        }
