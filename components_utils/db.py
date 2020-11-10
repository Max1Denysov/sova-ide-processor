from models import ComplectRevisionSeq
from sqlalchemy.dialects.postgresql import insert


def get_next_complect_revision_number(complect_id, session) -> int:
    """
        Возвращает очередное (у комплекта с "complect_id") значение для поля
        "revision_number" для новой строки в таблице "complects_revisions".

        (функция должна вызываться только при процессе вставки новой строки в
        таблицу "complects_revisions")
    """
    q = insert(ComplectRevisionSeq).values(
        complect_id=complect_id, last_revision_number=1
    ).on_conflict_do_update(
        index_elements=['complect_id'],
        set_=dict(
            last_revision_number=(ComplectRevisionSeq.last_revision_number + 1)
        )
    ).returning(ComplectRevisionSeq.last_revision_number)

    revision_number = session.execute(q).fetchone()[0]

    return revision_number


def get_next_complect_revision_number_rawsql(complect_id, session) -> int:
    """
        (версия на "сыром" sql)
        Возвращает очередное (у комплекта с "complect_id") значение для поля
        "revision_number" для новой строки в таблице "complects_revisions".

        (функция должна вызываться только при процессе вставки новой строки в
        таблицу "complects_revisions")
    """
    q = '''
        INSERT INTO complects_revisions_seq
            (complect_id, last_revision_number) VALUES (%s, 1)
        ON CONFLICT (complect_id) DO UPDATE
            SET last_revision_number =
                complects_revisions_seq.last_revision_number + 1
        RETURNING last_revision_number;
    ''' % str(complect_id)

    revision_number = session.execute(q).fetchone()[0]

    return revision_number
