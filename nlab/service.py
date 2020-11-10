import distutils.util
import json
import os

from jaeger_client import Config, span
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span, span_in_context


class Tracer(object):

    DEFAULT_JAEGER_CONFIG = {
      "sampler": {
        "type": "const",
        "param": 1,
      },
      "logging": False,
      "local_agent": {
        "reporting_host": "jaeger",
      }
    }


    """ Базовый класс для работы с opentracing системой. """
    def __init__(self, servicename, config=None):
        self.__service_name = servicename or ''
        self.__tracer = None

        if config:
            Tracer.configure(self, config)

    def _read_config(self, config):
        if not config:
            config = {}
        elif isinstance(config, str):
            config = json.load(open(config, 'r'))
        elif not isinstance(config, dict):
            raise ValueError("Invalid config: %s" % config)

        return config

    def configure(self, config):
        """ Разбор конфигурационного файла.

        :param str, dict config: Путь к конфигурационному файлу, либо dict с конфигурацией.
        """
        config = self._read_config(config)

        # Разбор конфигурации трейсинга из конфигурационного файла.
        # @todo !

        tracer_config = config.get("tracer", {}).get("config", self.DEFAULT_JAEGER_CONFIG)
        if(os.getenv('NLAB_JAEGER_HOST')):
            tracer_config['local_agent']['reporting_host'] = os.getenv('NLAB_JAEGER_HOST')
        if(os.getenv('NLAB_JAEGER_LOGGING')):
            tracer_config['logging'] = bool(distutils.util.strtobool(os.getenv('NLAB_JAEGER_LOGGING')))
        # Инициализация трейсера.
        self.__tracer = Config(
            config=tracer_config,
            service_name=self.__service_name,
            validate=True,
        ).initialize_tracer()

        return config

    def tracer(self):
        """ Получение доступа к трейсеру напрямую. """
        return self.__tracer

    def start_span(self, class_name, method_name, parent=None):
        """ Начало нового промежутка трассировки.

        :param str class_name: Название класса.
        :param str method_name: Название метода.
        :param parent: Информация для связи с родительским промежутком трассировки (либо объект span, либо данные полученные через trace_id).
        """
        if parent:
            if isinstance(parent, dict):
                parent = self.tracer().extract(Format.TEXT_MAP, parent)
            elif not isinstance(parent, span):
                raise RuntimeError('Invalid parent object: ', parent)
        else:
            parent = get_current_span()
        return self.tracer().start_span((class_name or 'class_name') + '.' + method_name, child_of=parent or get_current_span())

    def trace_id(self, span):
        """ Получение идентификационных данных промежутка трассировки для передачи в другой сервис. """
        trace = {}
        self.tracer().inject(span, Format.TEXT_MAP, trace)
        return trace
