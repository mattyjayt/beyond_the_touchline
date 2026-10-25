import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def app_client():
    # One lifespan per process: the MCP session manager can only run once.
    with TestClient(app) as c:
        yield c
