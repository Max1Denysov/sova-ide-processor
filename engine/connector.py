import settings

from engine.backend import EngineBackend
from engine.backends.docker import DockerBackend
from engine.backends.kubernetes import KubernetesBackend
from engine.backends.virtual_machine import VirtualMachineBackend


class EngineConnectorImpl:
    """
    Connector to engines: ssh dedicated or dockered compilers are supported
    """
    def create_backend(self, target, engine_info) -> EngineBackend:
        engine_type = engine_info.get("type")

        if engine_type == "kubernetes":
            return self._create_kubernetes_backend(target, engine_info)
        else:
            return self._create_ssh_backend(target, engine_info)

    def _create_ssh_backend(self, target, engine_info):
        user_info = settings.ENGINE_AUTH[engine_info["user"]]
        private_key = user_info["private_key"]
        data_path = engine_info["data_path"]
        container_name = engine_info.get("container_name")

        if container_name:
            return DockerBackend(
                target=target,
                user=engine_info["user"],
                host=engine_info["host"],
                engine_path=engine_info["engine_path"],
                private_key=private_key,
                data_path=data_path,
                container_name=container_name,
            )
        else:
            return VirtualMachineBackend(
                target=target,
                user=engine_info["user"],
                host=engine_info["host"],
                engine_path=engine_info["engine_path"],
                private_key=private_key,
                data_path=data_path,
            )

    def _create_kubernetes_backend(self, target, engine_info):
        pod_name = engine_info["pod_name"]

        kube_config_path = engine_info["kube_config_path"]
        kube_namespace = engine_info["kube_namespace"]

        return KubernetesBackend(
            pod_name=pod_name,
            kube_config_path=kube_config_path,
            kube_namespace=kube_namespace,
        )
