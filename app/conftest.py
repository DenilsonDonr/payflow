import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    """One client for the whole session, entered as a context manager on purpose.

    Outside one, TestClient spins a fresh event loop per request; the app's async pool, opened on
    the first request, would then belong to a loop that is already gone by the second. The context
    manager also runs the lifespan, so the pool opens and closes where the app says it should.

    It lives here, above every module, because the pool is process-wide: a second session client
    in another module would reopen it on its own loop and break whichever ran first.
    """
    with TestClient(app) as test_client:
        yield test_client
