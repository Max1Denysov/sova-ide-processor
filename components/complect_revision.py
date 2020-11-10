from components_utils.db import get_next_complect_revision_number
from components_utils.web import get_complect_code
from models import ComplectRevision
from nlab.rpc import ApiError, RpcGroup, rpc_name
from nlab.rpc.object import VersionObject


class ComplectRevisionRpc(RpcGroup):

    def __init__(self, tracer, create_session) -> None:

        super().__init__(
            name="complect_revision", tracer=tracer,
            create_session=create_session
        )

        self.complect_revision = VersionObject(
            name=self.name, primary_key="revision_id", entity=ComplectRevision,
            create_session=create_session
        )

    @rpc_name("list")
    def list_of_complect_revisions(self, complect_id=None, offset=None,
                                   limit=None, order=None) -> dict:
        """
            Возвращает строки из таблицы "revisions" для комплекта
            с "complect_id" (в словаре).
        """
        # TODO: Надо вынести отсюда эту функцию (и желательно переименовать)
        def form_items(items):
            return [item[0].to_dict() for item in items]

        # Подготовим фильтр по complect_id для будущего запроса
        filter_q = []
        if complect_id is not None:
            filter_q.append(ComplectRevision.complect_id == complect_id)

        # Запрос
        items, total_items = self.complect_revision.filter(
            filter_q=filter_q,
            offset=offset, limit=limit, form_items=form_items, order=order,
        )

        return {"items": items, "total": total_items}

    def fetch(self, id):
        """ Returns complect revision model by id """
        with self.create_session() as session:
            complect_revision_model = self.complect_revision.get(
                id, session=session)
            if not complect_revision_model:
                raise ApiError(
                    code="NOT_EXISTS",
                    message="Can't find complect revision with id=%r" % id
                )
            return complect_revision_model.to_dict()

    def _get_complect_code(self, complect_id):

        return get_complect_code(complect_id)

    def _make_complect_revision_code(self,
                                     complect_code, revision_number) -> str:
        """
            Возвращает значение для поля "code" для новой строки в таблице
            "complects_revisions"
        """
        return str(complect_code) + '.' + str(revision_number)

    def _create(self, complect_id, source_archive_path, binary_path, meta) \
            -> dict:
        """
            Создает новую строку в таблице "complects_revisions" для комплекта
            с "complect_id".

            Возвращает созданную строку (в словаре).
        """
        with self.create_session() as session:

            revision_number = get_next_complect_revision_number(
                complect_id, session
            )

            self.complect_code = self._get_complect_code(complect_id)

            code = self._make_complect_revision_code(
                self.complect_code, revision_number
            )

            complect_revision_model = ComplectRevision(
                complect_id=complect_id,
                revision_number=revision_number,
                code=code,
                source_archive_path=source_archive_path,
                binary_path=binary_path,
                meta=meta,
            )

            session.add(complect_revision_model)
            session.commit()

            return complect_revision_model.to_dict()
