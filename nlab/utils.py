import base64
import functools
import inspect
import json
import warnings
from collections import namedtuple
from itertools import cycle

ContainerId = namedtuple("ContainerId", "inf_id, chat_id, msg_id")


def xor_key_decrypt(data, key):
    data = base64.b64decode(data).decode("utf-8")
    xored = ''.join(chr(ord(x) ^ ord(y)) for x, y in zip(data, cycle(key)))
    xored = base64.b64decode(xored.encode("utf-8")).decode("utf-8")
    return xored


def decrypt_id(data):
    MSG_SECRET = "UNhdE39gf0VXG/r6fc8LWpqY"
    res = xor_key_decrypt(data, MSG_SECRET)
    res = json.loads(res)
    return ContainerId(inf_id=res["i"], chat_id=res["c"], msg_id=res["m"])


def deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    if isinstance(reason, str):

        # The @deprecated is used with a 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated("please, use another function")
        #    def old_function(x, y):
        #      pass

        def decorator(func1):

            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @functools.wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter('always', DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2
                )
                warnings.simplefilter('default', DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):

        # The @deprecated is used without any 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated
        #    def old_function(x, y):
        #      pass

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {name}."
        else:
            fmt2 = "Call to deprecated function {name}."

        @functools.wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2
            )
            warnings.simplefilter('default', DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))
