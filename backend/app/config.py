"""Runtime configuration.

A single root `.env` holds two sections, LOCAL_* and CLOUD_*. `APP_MODE`
selects which section is active; the properties on `Settings` resolve the
active value so the rest of the app never reads LOCAL_/CLOUD_ keys directly.
`scripts/run.sh --mode <mode>` exports APP_MODE, which overrides `.env`.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"

Mode = Literal["local", "cloud"]
AgentProvider = Literal["rules", "claude_code", "foundry"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # --- switch -------------------------------------------------------------
    app_mode: Mode = "local"

    # --- shared -------------------------------------------------------------
    sim_seed: int = 2026
    replay_speed: float = 10.0
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- local --------------------------------------------------------------
    local_api_base_url: str = "http://127.0.0.1:8000"
    local_database_url: str = "sqlite:///backend/data/beyond_the_touchline.db"
    local_data_dir: str = "backend/data"
    local_agent_provider: AgentProvider = "claude_code"

    # --- cloud (populated by infra provisioning later) ----------------------
    cloud_api_base_url: str = ""
    cloud_database_url: str = ""
    cloud_data_dir: str = ""  # Blob container URL
    cloud_agent_provider: AgentProvider = "foundry"
    cloud_realtime_url: str = ""
    cloud_foundry_endpoint: str = ""
    cloud_foundry_agent_id: str = ""
    cloud_appinsights_connection_string: str = ""

    def _active(self, name: str) -> str:
        return getattr(self, f"{self.app_mode}_{name}")

    @property
    def api_base_url(self) -> str:
        return self._active("api_base_url")

    @property
    def agent_provider(self) -> AgentProvider:
        return self._active("agent_provider")

    @property
    def database_url(self) -> str:
        url = self._active("database_url")
        # Relative SQLite paths are resolved against the repo root so the
        # backend behaves the same regardless of the working directory.
        prefix = "sqlite:///"
        if url.startswith(prefix) and not url.startswith(prefix + "/"):
            return prefix + str(ROOT_DIR / url[len(prefix) :])
        return url

    @property
    def data_dir(self) -> Path:
        path = Path(self._active("data_dir"))
        return path if path.is_absolute() else ROOT_DIR / path

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
