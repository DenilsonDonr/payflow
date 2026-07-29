import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

user = os.environ["POSTGRES_USER"]
password = os.environ["POSTGRES_PASSWORD"]
database = os.environ["POSTGRES_DB"]
host = os.environ["POSTGRES_HOST"]
port = os.environ["POSTGRES_PORT"]

class ConnectionDB:
    def __init__(self):
        self.conn = None

    def connect(self) -> psycopg.Connection:
        self.conn = psycopg.connect(
            f"dbname={database} user={user} password={password} host={host} port={port}"
        )
        return self.conn
    
    def get_connection(self) -> psycopg.Connection:
        if self.conn is None:
            return self.connect()

        try:
            self.conn.execute("SELECT 1")
        except psycopg.OperationalError:
            return self.connect()

        return self.conn
    
    def close(self) -> bool:
        if self.conn:
            self.conn.close()
            print("PostgreSQL connection closed.")
            return True
        return False