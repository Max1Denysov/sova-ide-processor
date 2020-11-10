import functools
import json
from datetime import datetime, date, timezone

from jsonrpcserver.methods import Methods

from nlab import elk
from nlab.service import Tracer
from sqlalchemy.orm import sessionmaker

from nlab.rpc.exceptions import ApiError


_RPC_NAME_ATTR = "_rpc_name"


def rpc_name(name):
    def decorator(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            return func(*args, **kwargs)

        new_func.__dict__[_RPC_NAME_ATTR] = name
        return new_func

    return decorator


def _json_serial(obj):
    if isinstance(obj, datetime):
        serial = obj.replace(tzinfo=timezone.utc).timestamp()
        return int(serial)

    if isinstance(obj, date):
        DAY = 24 * 60 * 60  # POSIX day in seconds (exact value)
        timestamp = (obj - date(1970, 1, 1)).days * DAY
        return timestamp

    raise TypeError("Type %s not serializable" % type(obj))


def transform_response(resp):
    """
    Заменяем даты на таймстемпы. Возможно самый короткий
    код для преобразования. Хотя и затратный.
    """
    return json.loads(json.dumps(resp, ensure_ascii=False,
                             default=_json_serial))


def _bind_tracer(group):
    def decorator(name, func, log):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            try:
                with group.tracer.start_span("service", name) as span:
                    status = True
                    errors = {}
                    try:
                        response = transform_response(func(*args, **kwargs))
                    except (ApiError,)  as e:
                        status = False
                        response = {}
                        log.exception("Api error")
                        errors = e.errors
                    except Exception as e:
                        status = False
                        response = {}
                        log.exception("Unhandled error")
                        errors = {
                            "message": str(e),
                            "code": "UNHANDLED",
                        }

                    result = {
                        "status": status,
                    }

                    if response:
                        result["response"] = response

                    if errors:
                        result["errors"] = errors

                    return result
            finally:
                pass

        return new_func

    return decorator


class RpcGroup:
    def __init__(self, name: str, tracer: Tracer, create_session: sessionmaker):
        self.name = name
        self.create_session = create_session
        self.log = elk.setup(service_name="arm", service_id="be", name=name)
        self.tracer = tracer
        self._parent_world = None

    def install(self, api_world: "ApiWorld", methods: Methods):
        self._parent_world = api_world

        tracer_binder = _bind_tracer(self)

        register = {}
        for method_name in dir(self):
            if method_name.startswith("_"):
                continue

            method = getattr(self, method_name)
            if not callable(method):
                continue

            register_name = getattr(method, _RPC_NAME_ATTR, method_name)
            register_rpc_name = "%s.%s" % (self.name, register_name)

            register[register_rpc_name] = tracer_binder(method_name,
                                                        method,
                                                        self.log)

        methods.add(**register)
