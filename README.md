# PROCESSOR

Входная точка запросов бекенда Арма.

## Установка зависимостей

Установка зависимостей:

    python3 -m venv venv
    venv/bin/pip install -r ./requirements.txt

Для компиляции (Debian зависимости). Не требуются, если не нужно запускать задачи с компиляцией:

    apt-get install -y php7.3 perl cpanminus make gcc
    cpanm Clone Algorithm::Combinatorics

## Алгоритм работы

Клиент отправляет запрос на сервис, в котором передает путь к функции `script`, которая будет выполняться для завершения задачи и аргументы `args`, с которыми она будет вызвана. Путь указывается относительно корня проекта. Желательно все скрипты располагать в папке `script`, чтобы они не были разбросаны по всему проекту.

    {
        "jsonrpc": "2.0",
        "method": "engine.create",
        "params": {
            "script": "tests.test_api.script_for_test_api.test_function",
            "args": {"test": 1, "other_test": 2},
            "meta": {}
        },
        "id": 1
    }

## Старт базы данных

Используется sqlalchemy. Для миграций нужен sqlalchemy alembic. Описывается структура таблиц и шаги миграции.

Для старта требуются база данных.

Для БД требуется инициализация uuid расширения:

    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

Миграции лежат в `alembic/`

При указанной переменной окружения `NLAB_ARM_DEV=1` настройки для соединения с БД alembic получает из файла `env/develop.env`.

Статус:

    NLAB_ARM_DEV=1 PYTHONPATH=. PYTHONPATH=. ./venv/bin/alembic current

При пустой базе покажется такое:

    INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
    INFO  [alembic.runtime.migration] Will assume transactional DDL.

Обновиться до последней ревизии:

    NLAB_ARM_DEV=1 venv/bin/alembic upgrade head

## Запуск сервиса

    source env/develop.env && \
        export $(cut -d= -f1 env/develop.env) && \
        venv/bin/python processor_server.py

Или так при использовании файла настроек `env/develop.env`:

    NLAB_ARM_DEV=1 venv/bin/python processor_service.py

## Запуск обработчика задач

    NLAB_ARM_DEV=1 venv/bin/python task_executor.py
