import sqlalchemy as sa
from nlab.conf import conf_attr
from sqlalchemy.orm import Session, sessionmaker


def create_engine(env_prefix):
    engine = sa.create_engine(make_sqla_database_uri(env_prefix=env_prefix))
    return engine


def make_sqla_database_uri(env_prefix=None):
    host, port, dbname, user, password = _get_conn_settings(env_prefix=env_prefix)
    return ("postgresql://{user}:{password}@{host}:{port}/{dbname}"
            .format(user=user, password=password, host=host, port=port, dbname=dbname))


def _get_conn_settings(host=None, port=None, dbname=None, user=None, password=None, env_prefix=None):
    if env_prefix is None:
        env_prefix = "NLAB_POSTGRES_"

    host = conf_attr(host, env=env_prefix + "HOST", default="localhost")
    port = conf_attr(port, parse_value=int, env=env_prefix + "PORT", default=5432)
    dbname = conf_attr(dbname, parse_value=str, env=env_prefix + "DB")
    user = conf_attr(user, parse_value=str, env=env_prefix + "USER")
    password = conf_attr(password, parse_value=str, env=env_prefix + "PASSWORD")
    return host, port, dbname, user, password


class SessionContext:
    def __init__(self, session: Session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


def _create_sessionmaker_caller(sessionmaker_):
    def creator():
        return SessionContext(sessionmaker_())

    return creator


def create_sessionmaker(env_prefix):
    engine = create_engine(env_prefix=env_prefix)
    sessionmaker_ = sessionmaker(bind=engine)
    return _create_sessionmaker_caller(sessionmaker_)


def next_seq_id(name, session):
    result = session.execute("SELECT nextval('%s')" % name)
    row = result.first()
    return row[0]
