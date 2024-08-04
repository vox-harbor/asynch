import ssl
from typing import Any, Optional

from asynch.connection import Connection
from asynch.proto.models.enums import ConnectionStatuses

HOST = "192.168.15.103"
PORT = 9000
USER = "default"
PASSWORD = ""
DATABASE = "default"


async def _get_tcp_connections_from_the_server(conn: Connection) -> int:
    stmt = "SELECT * FROM system.metrics WHERE metric LIKE '%Connection'"
    async with conn.cursor() as cursor:
        await cursor.execute(stmt)

        result = await cursor.fetchall()
        tcp_conn, num, _ = result[0]

        assert tcp_conn == "TCPConnection"
        return num


def _test_connection_credentials(
    conn: Connection,
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
) -> None:
    __tracebackhide__ = True

    assert conn.host == host
    assert conn.port == port
    assert conn.user == user
    assert conn.password == password
    assert conn.database == database


def _test_connectivity_invariant(
    conn: Connection, *, is_connected: Optional[bool] = None, is_closed: Optional[bool] = None
) -> None:
    __tracebackhide__ = True

    if is_connected is None:
        assert conn.connected is None
    else:
        assert conn.connected == is_connected

    if is_closed is None:
        assert conn.is_closed is None
    else:
        assert conn.is_closed == is_closed


def _test_basic_secure_settings(conn: Connection, *, ssl_options: dict[str, Any]) -> None:
    __tracebackhide__ = True

    ssl_opts = conn._connection.ssl_options

    assert conn._connection.secure_socket
    assert conn._connection.verify

    for key, value in ssl_options.items():
        if key == "ssl_version":
            assert value is ssl_opts[key]
            continue
        if value is None:
            assert ssl_opts.get(key) is None
            continue
        assert value == ssl_opts[key]


def test_dsn():
    dsn = f"clickhouse://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    conn = Connection(dsn=dsn)

    _test_connection_credentials(
        conn, host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE
    )
    _test_connectivity_invariant(conn=conn)


def test_secure_dsn():
    dsn = (
        f"clickhouses://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
        "?verify=true"
        "&ssl_version=PROTOCOL_TLSv1"
        "&ca_certs=path/to/CA.crt"
        "&ciphers=AES"
    )
    conn = Connection(dsn=dsn)

    _test_connection_credentials(
        conn, host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE
    )
    _test_connectivity_invariant(conn)
    _test_basic_secure_settings(
        conn,
        ssl_options={
            "ssl_version": ssl.PROTOCOL_TLSv1,
            "ca_certs": "path/to/CA.crt",
            "ciphers": "AES",
        },
    )


def test_secure_connection():
    conn = Connection(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        secure=True,
        verify=True,
        ssl_version=ssl.PROTOCOL_TLSv1,
        ca_certs="path/to/CA.crt",
        ciphers="AES",
    )

    _test_connection_credentials(
        conn, host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE
    )
    _test_connectivity_invariant(conn)
    _test_basic_secure_settings(
        conn,
        ssl_options={
            "ssl_version": ssl.PROTOCOL_TLSv1,
            "ca_certs": "path/to/CA.crt",
            "ciphers": "AES",
        },
    )


def test_secure_connection_check_ssl_context():
    conn = Connection(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        secure=True,
        ciphers="AES",
        ssl_version=ssl.OP_NO_TLSv1,
    )

    _test_connection_credentials(
        conn, host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE
    )
    _test_connectivity_invariant(conn)
    _test_basic_secure_settings(
        conn, ssl_options={"ssl_version": ssl.OP_NO_TLSv1, "ca_certs": None, "ciphers": "AES"}
    )

    ssl_ctx = conn._connection._get_ssl_context()
    assert ssl_ctx is not None
    assert ssl.OP_NO_TLSv1 in ssl_ctx.options


def test_connection_status_offline():
    conn = Connection()
    repstr = f"<connection object at 0x{id(conn):x}; " f"status: {ConnectionStatuses.created}>"

    assert repr(conn) == repstr
    assert conn.connected is None
    assert conn.is_closed is None


async def test_connection_status_online():
    conn = Connection()
    conn_id = id(conn)

    repstr = f"<connection object at 0x{conn_id:x}"
    assert repr(conn) == f"{repstr}; status: {ConnectionStatuses.created}>"

    try:
        await conn.connect()
        assert repr(conn) == f"{repstr}; status: {ConnectionStatuses.opened}>"
        assert conn.connected
        assert conn.is_closed is None

        await conn.close()
        assert repr(conn) == f"{repstr}; status: {ConnectionStatuses.closed}>"
        assert not conn.connected
        assert conn.is_closed
    finally:
        await conn.close()
        assert repr(conn) == f"{repstr}; status: {ConnectionStatuses.closed}>"
        assert not conn.connected
        assert conn.is_closed


async def test_tcp_connection_number():
    """Tests the number of TCP connections to the server.

    Only the connections from `conftest.py` should be taken into account.
    The order of test execution must not have any impact on this test.
    """

    conn = Connection()

    result = await _get_tcp_connections_from_the_server(conn)
    try:
        assert result == 3
    finally:
        await conn.close()
