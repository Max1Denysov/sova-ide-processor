import settings

from engine.backend import EngineBackend
from engine.connector import EngineConnectorImpl


class EngineFactory:
    """
    Engine backend factory
    """
    def __init__(self):
        self._impl: EngineConnectorImpl = EngineConnectorImpl()

    def create_compiler_backend(self, target) -> EngineBackend:
        """
        Create from compiler list hosts
        :param target:
        :return:
        """
        return self._create_backend(
            target, settings.ENGINE_COMPILER_HOSTS)

    def create_deployer_backend(self, target) -> EngineBackend:
        """
        Create from deploy list hosts

        :param target:
        :return:
        """
        return self._create_backend(
            target, settings.ENGINE_DEPLOY_HOSTS)

    def _create_backend(self, target, hosts) -> EngineBackend:
        host_info = hosts[target]
        return self._impl.create_backend(target, host_info)
