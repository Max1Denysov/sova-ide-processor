import asyncio
import traceback

import asyncpg
import nlab
import time

import nlab.logger
from nlab.conf import conf_attr
from nlab.utils import deprecated


@deprecated
def init_from_dict(env_prefix=None):
    return Postgres(env_prefix=env_prefix)


@deprecated
def make_sqla_database_uri(env_prefix=None):
    host, port, dbname, user, password = _get_conn_settings(env_prefix=env_prefix)
    return ("postgresql://{user}:{password}@{host}:{port}/{dbname}"
            .format(user=user, password=password, host=host, port=port, dbname=dbname))


class PostgresDBConn:
    def __init__(self, conn, logger):
        self.conn = conn
        self.logger = logger

    async def execute(self, query, *args):
        try:
            await self.conn.execute(query, *args)
        except:
            self.logger.exception("Error in db execute: %s; %s" % (query, args))
            raise


    async def executemany(self, query, args):
        try:
            await self.conn.executemany(query, args)
        except:
            self.logger.exception("Error in db executemany: %s; %s" % (query, args))
            raise


    async def fetch(self, query, *args):
        try:
            return await self.conn.fetch(query, *args)
        except:
            self.logger.exception("Error in db fetch: %s; %s" % (query, args))
            raise


    async def fetchrow(self, query, *args):
        try:
            return await self.conn.fetchrow(query, *args)
        except:
            self.logger.exception("Error in db fetchrow: %s; %s" % (query, args))
            raise


    async def fetchval(self, query, *args):
        try:
            return await self.conn.fetchval(query, *args)
        except:
            self.logger.exception("Error in db fetchval: %s; %s" % (query, args))
            raise

    async def executemany(self, query, args):
        try:
            await self. conn.executemany(query, args)
        except:
            self.logger.exception("Error in db executemany: %s; %s" % (query, args))
            raise


    async def executebatch(self, buildQuery, args, pagesize=5000, conn=None):
        if conn is None:
            conn = self.conn

        if not isinstance(args, list):
            args = list(args)

        npages = (len(args) + pagesize - 1) // pagesize

        for npage in range(npages):
            page = args[npage * pagesize:(npage + 1) * pagesize]

            query, queryArgs = buildQuery(page)

            try:
                await conn.execute(query, *queryArgs)
            except:
                self.logger.exception("Error in db query: %s; %s" % (query, queryArgs))
                raise


    def transaction(self):
        return self.conn.transaction()


class PostgresPoolProxy:
    def __init__(self, conn, logger):
        self.conn = conn
        self.logger = logger

    async def __aenter__(self):
        return PostgresDBConn(await self.conn.__aenter__(), logger=self.logger)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self.conn.__aexit__(exc_type, exc_val, exc_tb)


def _get_conn_settings(host=None, port=None, dbname=None, user=None, password=None, env_prefix=None):
    if env_prefix is None:
        env_prefix = "NLAB_POSTGRES_"

    host = conf_attr(host, env=env_prefix + "HOST", default="localhost")
    port = conf_attr(port, parse_value=int, env=env_prefix + "PORT", default=5432)
    dbname = conf_attr(dbname, parse_value=str, env=env_prefix + "DB")
    user = conf_attr(user, parse_value=str, env=env_prefix + "USER")
    password = conf_attr(password, parse_value=str, env=env_prefix + "PASSWORD")
    return host, port, dbname, user, password


@deprecated
class Postgres:
    def __init__(self, *, host=None, port=None, dbname=None, user=None, password=None,
                 ssl=False, startTimeout=15.0, startWait=0.5, connections=1, env_prefix=None, connectNow=True):

        q = dir(nlab)
        self.logger = nlab.logger.get('postgres')

        host, port, dbname, user, password = _get_conn_settings(host, port, dbname, user, password, env_prefix=env_prefix)

        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password

        self.ssl = ssl

        self.pool = None

        self.startConnect = None
        self.startTimeout = startTimeout
        self.startWait = startWait

        self.connections = connections

        if connectNow:
            self._connect_sync()

    def _connect_sync(self):
        i = 0
        self.startConnect = time.time()
        while time.time() - self.startConnect <= self.startTimeout:
            try:
                self.connect_sync()
            except (OSError, asyncpg.ConnectionDoesNotExistError, asyncpg.CannotConnectNowError) as e:
                print("Failed to connect to db on try #%s with error:\n%s\n%s" % (i + 1, e, traceback.format_exc()))
            finally:
                i += 1

            if self.pool is not None:
                break
            else:
                time.sleep(self.startWait)

        if self.pool is None:
            raise RuntimeError("Timeout reached while trying to connect to db '%s' as '%s'" % (self.dbname, self.user))

    async def connect(self):
        self.pool = await asyncpg.create_pool(host=self.host, port=self.port, database=self.dbname, ssl=self.ssl,
                                              user=self.user, password=self.password)

    async def execute(self, query, *args):
        try:
            await self.pool.execute(query, *args)
        except:
            self.logger.exception("Error in db execute: %s; %s" % (query, args))
            raise

    async def executemany(self, query, args):
        try:
            await self.pool.executemany(query, args)
        except:
            self.logger.exception("Error in db executemany: %s; %s" % (query, args))
            raise

    async def executebatch(self, buildQuery, args, pagesize=5000, conn=None):
        if conn is None:
            conn = self.pool

        if not isinstance(args, list):
            args = list(args)

        npages = (len(args) + pagesize - 1) // pagesize

        for npage in range(npages):
            page = args[npage * pagesize:(npage + 1) * pagesize]

            query, queryArgs = buildQuery(page)

            try:
                await conn.execute(query, *queryArgs)
            except:
                self.logger.exception("Error in db query: %s; %s" % (query, queryArgs))
                raise

    async def fetch(self, query, *args):
        try:
            return await self.pool.fetch(query, *args)
        except:
            self.logger.exception("Error in db fetch: %s; %s" % (query, args))
            raise

    async def fetchrow(self, query, *args):
        try:
            return await self.pool.fetchrow(query, *args)
        except:
            self.logger.exception("Error in db fetchrow: %s; %s" % (query, args))
            raise

    async def fetchval(self, query, *args):
        try:
            return await self.pool.fetchval(query, *args)
        except:
            self.logger.exception("Error in db fetchval: %s; %s" % (query, args))
            raise

    async def close(self):
        if self.pool is not None:
            await self.pool.close()

    def connect_sync(self):
        asyncio.get_event_loop().run_until_complete(self.connect())

    def acquire(self):
        return PostgresPoolProxy(self.pool.acquire(), self.logger)

    def release(self, conn):
        self.pool.release(conn)


