import sqlite3
import os


def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file"""
    try:
        os.unlink(db_file)
    except FileNotFoundError:
        pass
    conn = sqlite3.connect(db_file)
    return conn


def create_table(conn):
    """Create tables in the SQLite database"""
    sql_create_hosts_table = """ CREATE TABLE IF NOT EXISTS hosts (
                                        id integer PRIMARY KEY,
                                        ip_address text NOT NULL,
                                        fingerprint text NOT NULL,
                                        hostname text
                                    ); """

    sql_create_ports_table = """ CREATE TABLE IF NOT EXISTS ports (
                                        id integer PRIMARY KEY,
                                        host_id integer NOT NULL,
                                        port_number integer NOT NULL,
                                        service_name text,
                                        FOREIGN KEY (host_id) REFERENCES hosts (id)
                                    ); """

    c = conn.cursor()
    c.execute(sql_create_hosts_table)
    c.execute(sql_create_ports_table)


def insert_host(conn, host):
    """
    Insert a new host into the hosts table
    :param conn: Connection object
    :param host: A tuple (ip_address, hostname)
    :return: host id
    """
    sql = """ INSERT INTO hosts(ip_address, fingerprint, hostname)
              VALUES(?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, host)
    return cur.lastrowid


def insert_port(conn, port):
    """
    Insert a new port into the ports table
    :param conn: Connection object
    :param port: A tuple (host_id, port_number, service_name)
    """
    sql = """ INSERT INTO ports(host_id, port_number, service_name)
              VALUES(?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, port)
