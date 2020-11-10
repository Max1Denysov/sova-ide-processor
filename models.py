from datetime import datetime

from sqlalchemy.event import listens_for
from sqlalchemy.ext.declarative import declarative_base

from tables import (complects_revisions_seq_table, complects_revisions_table,
                    metadata, task_reports_table, tasks_table)

Base = declarative_base(metadata=metadata)


class Task(Base):
    __table__ = tasks_table

    task_id = tasks_table.c.task_id
    status = tasks_table.c.status
    script = tasks_table.c.script
    type = tasks_table.c.type
    args = tasks_table.c.args
    result = tasks_table.c.result
    errortext = tasks_table.c.errortext
    meta = tasks_table.c.meta
    extra = tasks_table.c.extra
    created = tasks_table.c.created
    updated = tasks_table.c.updated
    locked_by = tasks_table.c.locked_by

    ENQUEUED = "enqueued"
    WORKING = "working"
    FINISHED = "finished"
    FAILED = "failed"

    def to_dict(self):

        return {
            "task_id": self.task_id,
            "status": self.status,
            "success": self.get_success(),
            "meta": self.meta,
            "extra": self.extra,
            "created": self.created,
            "updated": self.updated,
            "errortext": self.errortext,
            "result": self.result,
        }

    def to_short_dict(self):

        return {
            "task_id": self.task_id,
            "status": self.status,
            "success": self.get_success(),
            "meta": self.meta,
            "extra": self.extra,
            "created": self.created,
            "updated": self.updated,
        }

    def get_success(self):

        return (self.result or {}).get("success")


class TaskReports(Base):
    __table__ = task_reports_table

    id = task_reports_table.c.id
    task_id = task_reports_table.c.task_id
    status = task_reports_table.c.status
    meta = task_reports_table.c.meta
    created = task_reports_table.c.created

    def to_dict(self):

        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status,
            "meta": self.meta,
            "created": self.created
        }


@listens_for(Task, 'after_update')
def task_after_update_function(mapper, connection, target):

    table = TaskReports.__table__
    connection.execute(
        table.insert().values(
            status=target.status, task_id=target.task_id,
            created=datetime.now()
        )
    )


class ComplectRevision(Base):
    __table__ = complects_revisions_table

    revision_id = complects_revisions_table.c.revision_id
    complect_id = complects_revisions_table.c.complect_id
    revision_number = complects_revisions_table.c.revision_number
    code = complects_revisions_table.c.code
    source_archive_path = complects_revisions_table.c.source_archive_path
    binary_path = complects_revisions_table.c.binary_path
    meta = complects_revisions_table.c.meta
    created = complects_revisions_table.c.created

    def to_dict(self):

        return {
            "id": self.revision_id,
            "complect_id": self.complect_id,
            "revision_number": self.revision_number,
            "code": self.code,
            "meta": self.meta,
            "created": self.created
        }


class ComplectRevisionSeq(Base):
    __table__ = complects_revisions_seq_table

    id = complects_revisions_seq_table.c.id
    complect_id = complects_revisions_seq_table.c.complect_id
    last_revision_number = complects_revisions_seq_table.c.last_revision_number
