from datetime import datetime

from models import Task
from nlab.rpc import ApiError, RpcGroup, rpc_name
from nlab.rpc.object import VersionObject
from sqlalchemy import Integer


class TaskRpc(RpcGroup):
    """Задача"""
    def __init__(self, tracer, create_session):

        super().__init__(
            name="task", tracer=tracer, create_session=create_session
        )
        self.task = VersionObject(
            name=self.name, primary_key="task_id", entity=Task,
            create_session=create_session
        )

    def create(self, script, type, args=None, meta=None, extra=None):
        """Создание"""

        return self._store(
            script=script, type=type, args=args, meta=meta, extra=extra
        )

    def info(self, task_id):
        """Получение задачи"""
        with self.create_session() as session:
            task_model = self.task.get(task_id, session=session)
            if not task_model:
                raise ApiError(
                    code="NOT_EXISTS",
                    message="Can't find task_id with id=%r" % task_id
                )

            return task_model.to_dict()

    @rpc_name("list")
    def list_(self, type,
              extra=None, offset=None, limit=None, order=None):
        """Получение списка"""

        def form_items(items):
            return [it[0].to_short_dict() for it in items]

        filter_q = [Task.type == type]

        if extra is not None and isinstance(extra, dict):
            for key, value in extra.items():
                if isinstance(value, int):
                    filter_q.append(
                        Task.extra[str(key)].astext.cast(Integer) == value
                    )
                else:
                    filter_q.append(
                        Task.extra[str(key)].astext == value
                    )

        items, total_items = self.task.filter(
            filter_q=filter_q, offset=offset, limit=limit,
            form_items=form_items, order=order
        )

        return {
            "items": items,
            "total": total_items,
        }

    def _store(self, script, type, args=None, meta=None, extra=None):

        with self.create_session() as session:

            task_model = Task(
                script=script,
                type=type,
                args=args,
                meta=meta,
                extra=extra,
                created=datetime.now(),
            )

            session.add(task_model)
            session.commit()

            return task_model.to_dict()
