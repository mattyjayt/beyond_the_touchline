from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.agent import tools
from app.agent.mcp_server import mcp
from app.agent.rules import RulesAgent
from app.api import router
from app.config import get_settings
from app.replay import ReplayManager
from app.store import Store

settings = get_settings()

# MCP gateway at /mcp/ (streamable HTTP). Mounted sub-app lifespans don't run,
# so the session manager is started in our lifespan below.
mcp_app = mcp.streamable_http_app(streamable_http_path="/", stateless_http=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = Store(Path(settings.database_url.removeprefix("sqlite:///")))
    replays = ReplayManager(store, settings.replay_speed)
    app.state.store, app.state.replays = store, replays
    tools.init(store, replays)
    rules = RulesAgent(store.demo_match_id)
    replays.get(store.demo_match_id)
    rules.start()
    async with mcp.session_manager.run():
        yield
    await rules.stop()
    await replays.close()


app = FastAPI(
    title="Inside the Game API",
    version=__version__,
    description="Synthetic football event replay, ratings and agent tools. All data is simulated.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.mount("/mcp", mcp_app)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "mode": settings.app_mode,
        "agent_provider": settings.agent_provider,
        "synthetic": True,
    }
