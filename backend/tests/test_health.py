from fastapi.testclient import TestClient

from app.config import ROOT_DIR, Settings
from app.main import app


def test_health_reports_mode_and_synthetic_flag():
    res = TestClient(app).get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["synthetic"] is True
    assert body["mode"] in {"local", "cloud"}


def test_mode_switch_selects_section():
    s = Settings(_env_file=None, app_mode="cloud", cloud_api_base_url="https://api.example")
    assert s.api_base_url == "https://api.example"
    assert s.agent_provider == "foundry"

    s = Settings(_env_file=None, app_mode="local")
    assert s.api_base_url == "http://127.0.0.1:8000"


def test_relative_sqlite_path_resolves_against_repo_root():
    s = Settings(_env_file=None, local_database_url="sqlite:///backend/data/x.db")
    assert s.database_url == f"sqlite:///{ROOT_DIR / 'backend/data/x.db'}"
