import distutils.util
import json
import logging
import os

import logstash_async.formatter
import logstash_async.handler

import nlab.exception
import nlab.logger


########################################################################################################################
#
#   Модуль для работы с системой логирования в elk.
#
########################################################################################################################


class LoggerFormatter(logging.Formatter):
    def __init__(self, extra=None):
        super().__init__(fmt="%(asctime)s %(name)-20s %(levelname)-7s %(message)s")
        self._extra = extra

    def format(self, record):
        # TODO: Return extra
        resp = super().format(record)
        return resp


class Formatter(logstash_async.formatter.LogstashFormatter):
    """Класс для форматирования сообщений, отправляемых в elk."""

    def format(self, record):
        message = json.loads(super().format(record))
        for field in ['service_name', 'service_id', 'module_name']:
            if field in message.get('extra'):
                message[field] = message['extra'][field]
                message['extra'].pop(field)
        return json.dumps(message)


class Adapter(logging.LoggerAdapter):
    """Адаптер для системы логирования, используемый для передачи дополнительных параметров."""

    def __init__(self, logger, module_name, extra={}):
        # Добавление имени модуля в контекст.
        extra.update({'module_name': 'nlab.' + str(module_name)})
        super().__init__(logger, extra)

    def process(self, msg, kwargs):
        # Объединение контекстов разных уровней.
        self.extra = kwargs.get('extra', {})
        self.extra['extras'] = dict(self.extra)
        return super().process(msg, kwargs)


def setup(service_name, service_id, host=None, port=5959, level=logging.ERROR, path='.nlab-logstash.db', nlablog=True, env=True, name="elk"):
    """Настройка системы логирования в elk.

    :param service_name: имя сервиса
    :param service_id: идентификатор сервиса
    :param host: имя сервера elk
    :param port: порт сервера elk
    :param level: уровень логирования
    :param path: путь к файлу для logstash'а
    :param nlablog: признак логирования всех записей также в стандартную систему логирования
    :param env: признак указывающий, использовать ли переменые окружения для конфигурации системы логирования
    """
    enabled = True

    if env:
        for arg in dict(os.environ).keys() & ['NLAB_ELK_HOST', 'NLAB_ELK_PORT', 'NLAB_ELK_LEVEL', 'NLAB_ELK_ENABLE']:
            key = arg[9:].lower()
            value = os.environ[arg]

            if value == '':
                continue

            if key == 'port':
                try:
                    port = int(value)
                except ValueError:
                    raise nlab.exception.NLabInvEnvValue(key, value)
            elif key == 'enable':
                try:
                    enabled = bool(distutils.util.strtobool(value))
                except ValueError:
                    raise nlab.exception.NLabInvEnvValue(key, value)

            elif key == 'host':
                host = value
            elif key == 'level':
                level = value

        log_to_std = os.getenv('NLAB_LOG_TO_STDERR')
        if log_to_std:
            try:
                nlablog = bool(distutils.util.strtobool(log_to_std))
            except ValueError:
                raise nlab.exception.NLabInvEnvValue('NLAB_LOG_TO_STDERR', log_to_std)

    if not host:
        enabled = False

    logger = logging.getLogger()
    logger.propagate = False
    logger.handlers.clear()

    extra = {'service_name': 'nlab.' + service_name, 'service_id': service_id}

    if nlablog:
        stream = logging.StreamHandler()
        stream.setFormatter(LoggerFormatter(extra=extra))
        logger.addHandler(stream)

    if enabled:
        # Соединение с elk производится только, если host указан напрямую.
        hndl = logstash_async.handler.AsynchronousLogstashHandler(host, port, database_path=path)
        hndl.setFormatter(Formatter(extra=extra))
        logger.addHandler(hndl)

    logger.setLevel(level)

    return logger


def get(module_name, **extra):
    """Получение системы логирования в elk.

    :param module_name: имя модуля
    :param kwargs: дополнительный контекст
    :return:
    """
    return Adapter(logging.getLogger('nlab.elk'), module_name, extra=extra)


class LogRequest:
    @staticmethod
    def form_headers(headers):
        """
        Формирование хэдеров
        """
        res = []
        for key, value in headers.items():
            res.append(f"{key}: {value}")

        return "\n".join(res)

    @staticmethod
    def form_body(body):
        """
        Формирование тела
        """
        if body and not isinstance(body, dict):
            body = json.loads(body)

        from nlab.rpc import transform_response
        return json.dumps(transform_response(body), indent=4, ensure_ascii=False)

    @classmethod
    def get_log(cls, r, type="POST"):
        """
        Формирование полного лога (запрос + ответ)
        """
        return f"{type} {r.request.url}\n" \
               f"{cls.form_headers(r.request.headers)}" \
               f"{cls.form_body(r.request.body)}" \
               "Response:" \
               f"{cls.form_headers(r.headers)}" \
               f"{cls.form_body(r.text)}"

    @classmethod
    def get_log_json(cls, r, type="POST"):
        """
        Формирование полного лога в виде JSON
        """
        return {"type": type,
                "request": {"headers": r.request.headers,
                            "body": r.request.body,
                            },
                "response": {"headers": r.headers,
                             "body": r.text,
                             }
                }
