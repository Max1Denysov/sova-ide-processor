import reprlib


class ServerApiError(Exception):
    code = '*'
    text = 'unknown'

    def __str__(self):
        return reprlib.repr(self.text)

    def __doc__(self):
        return reprlib.repr(self.text)


class ServerApiAuthError(ServerApiError):
    pass


class ServerApiAuthKeyNotExistError(ServerApiAuthError):
    text = "Authentication key is not specified"


class ServerApiAuthWrongKeyError(ServerApiAuthError):
    text = "Authentication key is not valid"


class ServerApiWebhookError(ServerApiError):
    pass


class ServerApiWebhookConnectError(ServerApiWebhookError):
    text = "Ошибка при отправке запроса к webhook"


class ServerApiWebhookHttpsError(ServerApiWebhookError):
    text = "Webhook использует отличный от https протокол"


class ServerApiWebhookResponseError(ServerApiWebhookError):
    text = "Webhook вернул неверный ответ"


class ServerApiWebhookStatusError(ServerApiWebhookError):
    text = "Webhook вернул неверный ответ"


class ServerApiRequestError(ServerApiError):
    text = "Неверный формат данных в запросе"


class MsgrProxyError(ServerApiError):
    text = "Ошибка MsgrProxy"


class Common:
    code = '*'
    text = 'unknown'

    def __str__(self):
        return reprlib.repr(self.text)

    def __doc__(self):
        return reprlib.repr(self.text)


class CommonLogger(Common):
    pass


class CommonLoggerNotSet(CommonLogger):
    text = "Логгер не установлен"
