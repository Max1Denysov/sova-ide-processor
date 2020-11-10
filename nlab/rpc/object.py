import sqlalchemy as sa
from sqlalchemy import desc, asc, or_, and_
from nlab.rpc.exceptions import ApiError


class VersionNoObject(ValueError):
    def __init__(self, msg, filter_q=None):
        super().__init__(msg)
        self.filter_q = filter_q


class VersionObject:
    def __init__(self, name, primary_key, entity,
                 create_session, versions_entity=None):
        self.name = name
        self.primary_key = primary_key
        self.entity = entity
        self.versions_entity = versions_entity
        self.create_session = create_session

    def filter(self, *, offset=None, limit=None, filter_q=None, filter_by_q=None, join=None, outerjoin=None, fetch_args=None,
               group_by=None, order=None, form_items=None):
        with self.create_session() as session:
            q = self.prepare_filter_q(offset=offset, limit=limit, filter_q=filter_q, filter_by_q=filter_by_q,
                                      join=join, outerjoin=outerjoin, fetch_args=fetch_args, group_by=group_by,
                                      session=session, order=order)

            items = q.all()
            total_items = 0
            if items:
                total_items = items[0][1]
            result_items = form_items(items) if form_items else [it[0].to_dict() for it in items]

            return result_items, total_items

    def versions(self, id, *, order=None, offset=None, limit=None,
                 filter_q=None, filter_by_q=None, fetch_args=None,
                 form_items=None):

        with self.create_session() as session:
            q = self.prepare_versions_q(
                id,
                offset=offset,
                limit=limit,
                filter_q=filter_q,
                filter_by_q=filter_by_q,
                fetch_args=fetch_args,
                session=session,
                order=order,
            )

            items = q.all()
            total_items = 0
            if items:
                total_items = items[0][1]
            result_items = form_items(items) if form_items else [it[0].to_dict()
                                                                 for it in
                                                                 items]

            return result_items, total_items

    def prepare_versions_q(self, id, *, session, order=None, offset=None,
                           limit=None, filter_q=None, filter_by_q=None,
                           fetch_args=None):
        if not order and hasattr(self.versions_entity, "version"):
            order = {"field": "version", "order": 1}

        if fetch_args is None:
            fetch_args = []

        q = session.query(
            self.versions_entity,
            sa.over(sa.func.count()).label("total_items"),
            *fetch_args,
        )

        if not isinstance(id, list):
            id = [id]

        q = q.filter(self._version_object_key_field().in_(id))

        if filter_q:
            q = q.filter(*filter_q)

        if filter_by_q:
            q = q.filter_by(**filter_by_q)

        if order:
            q = self._add_versions_order(q, order)

        q = q.offset(offset).limit(limit)

        return q


    def prepare_filter_q(self, *, session, offset=None, limit=None, filter_q=None, filter_by_q=None, join=None,
                         fetch_args=None, group_by=None, outerjoin=None,
                         order=None):
        if not order and hasattr(self.entity, "created"):
            order = {"field": "created", "order": 1}

        if fetch_args is None:
            fetch_args = []

        q = session.query(
            self.entity,
            sa.over(sa.func.count()).label("total_items"),
            *fetch_args,
        )

        if join:
            q = q.join(*join)

        if outerjoin:
            q = q.outerjoin(*outerjoin)

        if filter_q:
            q = q.filter(*filter_q)

        if filter_by_q:
            q = q.filter_by(**filter_by_q)

        if group_by:
            q = q.group_by(*group_by)

        if offset is None:
            offset = 0

        if limit is None:
            limit = 50

        if order:
            q = self._add_order(q, order)

        q = q.offset(offset).limit(limit)

        return q

    def get(self, id, *, session=None):
        if session:
            it = self._fetch(id, session=session)
        else:
            with self.create_session() as session:
                it = self._fetch(id, session=session)

        return it

    def remove(self, id, session=None):
        if session:
            return self._remove(id=id, session=session)
        else:
            with self.create_session() as session:
                return self._remove(id=id, session=session)

    def _validate_id(self, id):
        if not len(self.primary_key) == len(id):
            raise ValueError("The count of fields in the primary key and the count of arguments do not match.")

        return True

    def _fetch(self, pk=None, *, session, query_result=False, **kwargs):
        if not ((pk is not None) ^ bool(kwargs)):
            raise RuntimeError("Either pk or kwargs must be given!")

        if pk is not None:
            if isinstance(self.primary_key, tuple):
                self._validate_id(pk)

                kwargs = dict(zip(self.primary_key, pk))
            else:
                kwargs = {self.primary_key: pk}

        it = session.query(self.entity).filter_by(**kwargs)

        try:
            it_first = it.first()
        except sa.exc.DataError:
            raise ApiError(message="Invalid object id in request", code="INVALID_PARAMS")

        return (it_first, it) if query_result else it_first

    def _remove(self, id, session):
        if not isinstance(id, list):
            id = [id]

        success = True
        if isinstance(self.primary_key, str):  # если первичный ключ состоит из одного поля
            query_result = session.query(self.entity).filter(self._primary_key_field().in_(id))
        else:
            and_list = [and_(*[self._primary_key_field(field) == value
                             for field, value in zip(self.primary_key, item)]) for item in id
                        if self._validate_id(item)]

            query_result = session.query(self.entity).filter(or_(*[item for item in and_list]))

        query_result.delete(synchronize_session=False)
        session.commit()
        return success

    def _primary_key_field(self, field=None):
        primary_key_field = getattr(self.entity, field or self.primary_key)
        return primary_key_field

    def _version_object_key_field(self, field=None):
        key_field = getattr(self.versions_entity, field or self.primary_key)
        return key_field

    def _is_order_item_valid(self, item):
        if not isinstance(item, dict) or len(item) != 2:
            return False, "All sort field items must be dict with size 2"

        field = item.get("field", "")
        if field not in self.entity.__dict__:
            return False, "No such name '%s' for sorting order" % field

        order = item.get("order")
        if order not in (1, -1):
            return False, "Order of sorting column %s must be integer 1 or " \
                          "-1" % field

        return True, None

    def _validate_order(self, order):
        if order is None:
            return

        if not isinstance(order, list):
            raise ValueError("Sort field must be list of sorting items or dict")

        for item in order:
            valid, text = self._is_order_item_valid(item)
            if not valid:
                raise ValueError(text)

    def _add_order(self, q, order):
        if isinstance(order, dict):
            order = [order]
        self._validate_order(order)
        sort_direct = lambda field, order: asc(field) if order == 1 else \
            desc(field)
        sorting = [sort_direct(self.entity.__dict__[item["field"]],
                               item["order"]) for item in order]
        return q.order_by(*sorting)

    def _add_versions_order(self, q, order):
        if isinstance(order, dict):
            order = [order]
        self._validate_order(order)
        sort_direct = lambda field, order: asc(field) if order == 1 else \
            desc(field)
        sorting = [sort_direct(self.versions_entity.__dict__[item["field"]],
                               item["order"]) for item in order]
        return q.order_by(*sorting)
