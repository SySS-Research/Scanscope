import os
import sqlite3


def create_connection(db_file: str) -> sqlite3.Connection:
    """Create a database connection to the SQLite database specified by db_file"""
    try:
        os.unlink(db_file)
    except FileNotFoundError:
        pass
    conn = sqlite3.connect(db_file)
    return conn


def create_table(conn: sqlite3.Connection) -> None:
    """Create tables in the SQLite database"""
    sql_create_hosts_table = """
    CREATE TABLE IF NOT EXISTS hosts (
        id integer PRIMARY KEY,
        ip_address text NOT NULL,
        ip_address_int integer NOT NULL,
        fingerprint text,
        os text,
        hostname text
    );"""
    sql_create_index_on_hosts = """
    CREATE INDEX idx_%(column)s ON hosts (%(column)s);
    """

    sql_create_ports_table = """
    CREATE TABLE IF NOT EXISTS ports (
        id integer PRIMARY KEY,
        host_id integer NOT NULL,
        port_number integer NOT NULL,
        service_name text,
        FOREIGN KEY (host_id) REFERENCES hosts (id)
    );"""
    sql_create_ports_index = """
    CREATE INDEX idx_host_id ON ports (host_id);
    """

    c = conn.cursor()
    c.execute(sql_create_hosts_table)
    c.execute(sql_create_ports_table)
    for column in "ip_address ip_address_int fingerprint hostname".split():
        c.execute(sql_create_index_on_hosts % dict(column=column))
    c.execute(sql_create_ports_index)


def insert_host(conn: sqlite3.Connection, host: tuple[str, int, str | None, str | None, str | None]) -> int | None:
    """
    Insert a new host into the hosts table
    :param conn: Connection object
    :param host: A tuple (ip_address, ip_address_int, fingerprint, hostname, os)
    :return: host id
    """
    sql = """ INSERT INTO hosts(ip_address, ip_address_int, fingerprint, hostname, os)
              VALUES(?,?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, host)
    return cur.lastrowid


def insert_port(conn: sqlite3.Connection, port: tuple[int | None, int, str]) -> None:
    """
    Insert a new port into the ports table
    :param conn: Connection object
    :param port: A tuple (host_id, port_number, service_name)
    """
    sql = """ INSERT INTO ports(host_id, port_number, service_name)
              VALUES(?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, port)
