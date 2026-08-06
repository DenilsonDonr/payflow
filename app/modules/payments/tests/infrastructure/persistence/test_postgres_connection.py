import psycopg
import pytest

from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB

pytestmark = pytest.mark.integration

@pytest.fixture
def connection_db():
    db_connection = ConnectionDB()

    try:
        db_connection.connect()
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests.")

    yield db_connection

    db_connection.close()

class TestConnectionDB:
    def test_returns_a_working_connection(self, connection_db: ConnectionDB):
        conn = connection_db.get_connection()

        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)

    def test_reconnects_if_connection_is_closed(self, connection_db: ConnectionDB):
        conn = connection_db.get_connection()

        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)

        # close connection
        conn.close()

        # get connection again
        conn = connection_db.get_connection()

        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)
