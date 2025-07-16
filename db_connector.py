import psycopg2
import sshtunnel
import os

def get_db_connection():
    tunnel = sshtunnel.SSHTunnelForwarder(
        (os.getenv("SSH_HOST"), 22),
        ssh_username=os.getenv("SSH_USER"),
        ssh_password=os.getenv("SSH_PASSWORD"),
        remote_bind_address=('127.0.0.1', 5432),
        local_bind_address=('127.0.0.1', 5433)
    )
    tunnel.start()

    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host='127.0.0.1',
        port=5433
    )

    return conn, tunnel