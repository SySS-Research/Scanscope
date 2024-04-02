import sqlite3
import os


def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file"""
    os.unlink(db_file)
    conn = sqlite3.connect(db_file)
    return conn


def create_table(conn):
    """Create tables in the SQLite database"""
    sql_create_hosts_table = """ CREATE TABLE IF NOT EXISTS hosts (
                                        id integer PRIMARY KEY,
                                        ip_address text NOT NULL,
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
    sql = ''' INSERT INTO hosts(ip_address, hostname)
              VALUES(?,?) '''
    cur = conn.cursor()
    cur.execute(sql, host)
    conn.commit()
    return cur.lastrowid


def insert_port(conn, port):
    """
    Insert a new port into the ports table
    :param conn: Connection object
    :param port: A tuple (host_id, port_number, port_type, service_name)
    """
    sql = ''' INSERT INTO ports(host_id, port_number, port_type, service_name)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, port)
    conn.commit()


# Example usage
def main():
    database = "hosts_ports.db"

    # create a database connection
    conn = create_connection(database)
    with conn:
        create_table(conn)

        # Insert host data
        host_data = ('192.168.1.1', 'example_host')
        host_id = insert_host(conn, host_data)

        # Insert port data
        port_data = [
            (host_id, 80, 'TCP', 'http'),
            (host_id, 443, 'TCP', 'https'),
            (host_id, 53, 'UDP', 'dns')
        ]
        for port in port_data:
            insert_port(conn, port)

if __name__ == '__main__':
    main()

