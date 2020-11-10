import json
import logging
import re

########################################################################################################################
#
#   Модуль для работы с системой логирования на основе модуля logging.
#
########################################################################################################################

# @todo Разбор конфигурации системы логирования из файла/словаря.

# Дублирование уровней логирования для более удобного использования.
import warnings

from nlab.utils import deprecated

CRITICAL = logging.CRITICAL
FATAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG


class Logger(logging.LoggerAdapter):
    """Декоратор для системы логирования, используемый для корректного представления сообщений в логах."""

    @staticmethod
    def msg_format():
        """Получение стандартного формата для сообщений."""
        return '%(asctime)s %(name)-15s %(process)-8s %(levelname)-7s %(message)s'

    @staticmethod
    def date_format():
        """Получение стандартного формата для дат."""
        return '%Y.%m.%d %H:%M:%S'

    def process(self, msg, kwargs):
        """Обработка сообщения перед записью у лог.

        :param msg: сообщение
        :param kwargs: дополнительные аргументы
        """

        # Перевод мультистрочных сообщений в однострочные и экранирование спецсимволов.
        msg = re.sub('\\\\', '\\\\\\\\', msg)
        msg = re.sub('\n', '\\\\n', msg)
        msg = re.sub('"', '\\\\"', msg)

        # Получение дополнительного контекста к сообщениям.
        extra = {}
        if isinstance(self.extra, dict):
            extra.update(self.extra)
        extra.update(kwargs.get('extra', {}))

        # Обрамление сообщения двойными кавычками и добавление дополнительного контекста в виде JSON структуры.
        if extra:
            return '"%s" %s' % (msg, json.dumps(extra, ensure_ascii=False)), kwargs
        else:
            return '"%s"' % msg, kwargs


def __get(module_name=None):
    if module_name:
        return logging.getLogger('nlab.' + module_name)
    else:
        return logging.getLogger('nlab')


@deprecated("Use nlab.elk.get instead")
def get(module_name=None, **extra):
    """Получение логера для определенного модуля или всей системы в целом.

    :param module_name: имя модуля, если аргумент отсутствует, то будет возвращен модуль логирования для системы в целом
    :param extra: дополнительный контекст
    """
    return Logger(__get(module_name), extra=extra)


@deprecated("Use nlab.elk.setup instead")
def setup(nlab=True, msg_format=None, date_format=None, system=False, level=logging.ERROR):
    # @todo Проверка аргументов.

    # Получение системы логирования.
    logger = logging.getLogger() if system else __get()

    # Настройка наследования систем логирования.
    logger.propagate = system or not nlab

    # Удаление других систем логирования.
    if not system and nlab:
        for handler in logger.handlers:
            handler.acquire()
            handler.flush()
            logger.removeHandler(handler)
            handler.release()

    ch = logging.StreamHandler()

    # Настройка форматирования.
    formatter = logging.Formatter(
        fmt=msg_format if msg_format else Logger.msg_format(),
        datefmt=date_format if date_format else Logger.date_format())

    ch.setFormatter(formatter)

    if system or nlab:
        logger.addHandler(ch)
        logger.setLevel(level)

    return logger
