import json
import urllib

from nlab.rpc.exceptions import ApiError


def _make_params(args, kwargs):
    value = {}
    if len(args) >= 1:
        if not isinstance(args[0], dict):
            raise ValueError("Positional argument must be dict. Got: %s" % args)

        if kwargs:
            raise ValueError("Either positional args or kwargs must be given. Got: %s and %s" % (args, kwargs))

        value = args[0]

    if kwargs:
        value = kwargs

    return value


class _MethodComponentCall:
    def __init__(self, rpc, method):
        self.rpc = rpc
        self.method = method

    def __call__(self, *args, **kwargs):
        return getattr(self.rpc, self.method)(**_make_params(args, kwargs))


class _MethodComponent:
    def __init__(self, api, class_):
        self.api = api
        self.class_ = class_
        self.rpc = api.rpcs[class_]

    def __getattr__(self, method):
        return _MethodComponentCall(self.rpc, method)


class MethodClient:
    def __init__(self, api):
        self.api = api

    def component(self, component):
        return _MethodComponent(self.api, component)


class ProtocolError(RuntimeError):
    pass


class _WebComponentMethod:
    def __init__(self, component_name, url, method):
        self.component_name = component_name
        self.url = url
        self.method = method

    def __call__(self, *args, **kwargs):
        call = {
            "jsonrpc": "2.0",
            "method": "%s.%s" % (self.component_name, self.method),
            "params": _make_params(args, kwargs),
            "id": 1,
        }

        data = json.dumps(call).encode("utf-8")
        try:
            resp = urllib.request.urlopen(self.url, data=data)
        except urllib.error.HTTPError as e:
            raise ProtocolError("HTTP Error %s.%s %s: %s" % (self.component_name, self.method, str(e), e.read())) from e

        resp_data = json.load(resp)
        if not resp_data["result"]["status"]:
            errors = resp_data["result"]["errors"]
            raise ApiError(code=errors["code"], message=errors["message"])

        return resp_data["result"].get("response", {})


class _WebComponent:
    def __init__(self, *, url, component, api=None):
        self.component_name = component if isinstance(component, str) else api.rpcs[component].name
        self.url = url

    def __getattr__(self, method):
        return _WebComponentMethod(self.component_name, self.url, method)

    def list_all(self, **kwargs):
        list_method = getattr(self, "list")

        offset = 0
        LIMIT = 5000

        final_resp = None

        while True:
            resp = list_method(offset=offset, limit=LIMIT, **kwargs)
            if final_resp is None:
                final_resp = resp
            else:
                final_resp["items"].extend(resp["items"])
            if len(resp["items"]) < LIMIT:
                break

            offset += LIMIT

        return final_resp


class WebClient:
    def __init__(self, url, *, api=None):
        self.url = url
        self.api = api

    def component(self, component):
        return _WebComponent(api=self.api, url=self.url, component=component)
