import json
from typing import Dict

from jsonrpcserver import dispatch
from jsonrpcserver.methods import Methods, global_methods

from components.cluster import ClusterRpc
from components.complect_revision import ComplectRevisionRpc
from components.task import TaskRpc
from nlab.rpc import RpcGroup
from nlab.service import Tracer

# add all imported "rpc" classes here
RPC_CLASSES = (ComplectRevisionRpc, TaskRpc, ClusterRpc)


class ApiWorld:

    def __init__(self, create_session) -> None:

        self.create_session = create_session
        self.tracer = Tracer("proxy")
        self.tracer.configure({})

        params = {
            'tracer': self.tracer, 'create_session': self.create_session
        }

        self.rpcs: Dict[type, RpcGroup] = {
            rpc_class: rpc_class(**params) for rpc_class in RPC_CLASSES
        }

    def install(self, methods: Methods) -> None:

        for rpc in self.rpcs.values():
            rpc.install(self, methods)

    def call(self, *, method, params):
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }
        req_str = json.dumps(req)

        response = dispatch(
            request=req_str, methods=global_methods,
            debug=True, basic_logging=True
        )
        return response
