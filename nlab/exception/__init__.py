class NLabException(Exception):
    pass


class NLabMissedArgument(NLabException):
    def __init__(self, name):
        super().__init__("Missed argument: " + str(name))


class NLabInvalidArgumentType(NLabException):
    def __init__(self, name, value):
        super().__init__("Invalid type of argument '" + str(name) + "': " + str(value))


class NLabInvEnvValue(NLabException):
    def __init__(self, name, value):
        super().__init__("Invalid value of environment variable '" + str(name) + "': " + str(value))


class NLabValueError(NLabException):
    pass
