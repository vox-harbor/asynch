from typing import Optional

from asynch import errors
from asynch.cursors import Cursor
from asynch.proto import constants
from asynch.proto.connection import Connection as ProtoConnection
from asynch.proto.utils.dsn import parse_dsn


class Connection:
    def __init__(
        self,
        dsn: Optional[str] = None,
        user: str = constants.DEFAULT_USER,
        password: str = constants.DEFAULT_PASSWORD,
        host: str = constants.DEFAULT_HOST,
        port: int = constants.DEFAULT_PORT,
        database: str = constants.DEFAULT_DATABASE,
        cursor_cls=Cursor,
        echo: bool = False,
        stack_track: bool = False,
        **kwargs,
    ):
        if dsn:
            config = parse_dsn(dsn)
            self._connection = ProtoConnection(**config, stack_track=stack_track, **kwargs)
            user = config.get("user", None) or user
            password = config.get("password", None) or password
            host = config.get("host", None) or host
            port = config.get("port", None) or port
            database = config.get("database", None) or database
        else:
            self._connection = ProtoConnection(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                stack_track=stack_track,
                **kwargs,
            )
        self._dsn = dsn
        # dsn parts
        self._user = user
        self._password = password
        self._host = host
        self._port = port
        self._database = database
        # connection additional settings
        self._is_closed = None
        self._echo = echo
        self._cursor_cls = cursor_cls
        self._connection_kwargs = kwargs

    def __repr__(self):
        prefix = f"<connection object at 0x{id(self):x}; status: "
        if self.connected:
            prefix += "opened"
        elif self.is_closed:
            prefix += "closed"
        else:
            prefix += "created"
        return f"{prefix}>"

    @property
    def connected(self) -> Optional[bool]:
        return self._connection.connected

    @property
    def is_closed(self) -> Optional[bool]:
        return self._is_closed

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def user(self) -> str:
        return self._user

    @property
    def password(self) -> str:
        return self._password

    @property
    def database(self) -> str:
        return self._database

    @property
    def echo(self) -> bool:
        return self._echo

    async def close(self) -> None:
        if self._is_closed:
            return
        await self._connection.disconnect()
        self._is_closed = True

    async def commit(self):
        raise errors.NotSupportedError

    async def rollback(self):
        raise errors.NotSupportedError

    async def connect(self):
        if self.connected:
            return
        await self._connection.connect()

    def cursor(self, cursor: Optional[Cursor] = None) -> Cursor:
        cursor_cls = cursor or self._cursor_cls
        return cursor_cls(self, self._echo)


async def connect(
    dsn: str = None,
    user: str = constants.DEFAULT_USER,
    password: str = constants.DEFAULT_PASSWORD,
    host: str = constants.DEFAULT_HOST,
    port: int = constants.DEFAULT_PORT,
    database: str = constants.DEFAULT_DATABASE,
    cursor_cls=Cursor,
    echo: bool = False,
    **kwargs,
) -> Connection:
    conn = Connection(
        dsn=dsn,
        user=user,
        password=password,
        host=host,
        port=port,
        database=database,
        cursor_cls=cursor_cls,
        echo=echo,
        **kwargs,
    )
    await conn.connect()
    return conn
