from sqlalchemy import (BigInteger, Column, DateTime, ForeignKey, Integer,
                        MetaData, String, Table, func)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

metadata = MetaData()

TASK_STATUSES = ("enqueued", "working", "finished", "failed")
task_statuses = ENUM(*TASK_STATUSES, name="status")

tasks_table = Table(
    "tasks", metadata,

    Column(
        "task_id", UUID, server_default=func.uuid_generate_v4(),
        primary_key=True
    ),
    Column(
        "status", task_statuses, default="enqueued", nullable=False
    ),
    Column(  # путь к скрипту относительно
        "script", String, nullable=False
    ),
    Column(   # тип задачи
        "type", String, nullable=False
    ),
    Column(   # заблокирован задачей
        "locked_by", String, nullable=True
    ),
    Column(  # аргументы, которые будут переданы в функцию
        "args", JSONB
    ),
    Column(  # в это поле возможно сохранение результата
        "result", JSONB
    ),
    Column(  # текст ошибки
        "errortext", String
    ),
    Column(
        "meta", JSONB, server_default="{}", nullable=False
    ),
    Column(  # дополнительные поля (такие как complect_id и т.п...)
        "extra", JSONB, nullable=True  # индекс gin создан руками в миграции
    ),
    Column(
        "created", DateTime(timezone=True), nullable=False,
        server_default=func.now()
    ),
    Column(
        "updated", DateTime(timezone=True), nullable=True, onupdate=func.now()
    ),
)
# Внимание! Для таблицы "tasks" и поля "extra" рекомендуется создать
# gin-индекс.
#
# SQL для него такой:
#
# CREATE INDEX tasks_extra_index
#    ON tasks USING gin (extra)
#    WHERE extra IS NOT NULL;
#
# Создать индекс можно так:
# - Выполнить SQL скрипт в БД
# или
# - Добавить код создания и удаления индекса в миграцию (рекомендуемый способ)


task_reports_table = Table(
    "task_reports", metadata,

    Column(
        "id", BigInteger, primary_key=True, autoincrement=True
    ),
    Column(
        "task_id", UUID, ForeignKey("tasks.task_id"), nullable=False
    ),
    Column(
        "status", task_statuses, nullable=False
    ),
    Column(
        "meta", JSONB, server_default="{}", nullable=False
    ),
    Column(
        "created", DateTime(timezone=True), nullable=False,
        server_default=func.now()
    ),
)


complects_revisions_table = Table(
    "complects_revisions", metadata,

    Column(
        "revision_id", UUID, server_default=func.uuid_generate_v4(),
        primary_key=True
    ),
    Column(
        "complect_id", UUID, nullable=False,
    ),
    Column(
        "revision_number", Integer, nullable=False,
    ),
    Column(
        "code", String, nullable=False, unique=True,
    ),
    Column(
        "source_archive_path", String, nullable=False,
    ),
    Column(
        "binary_path", String, nullable=True,
    ),
    Column(
        "meta", JSONB, server_default="{}", nullable=False,
    ),
    Column(
        "created", DateTime(timezone=True), nullable=False,
        server_default=func.now()
    ),
)


complects_revisions_seq_table = Table(
    "complects_revisions_seq", metadata,

    Column(
        "id", BigInteger, primary_key=True, autoincrement=True,
    ),
    Column(
        "complect_id", UUID, nullable=False, unique=True,
    ),
    Column(
        "last_revision_number", Integer, nullable=False, default=1,
    ),
)
