from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import create_all
from src.routers import categories, organizations, sla_policies, tickets, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    # MVP: create tables on startup instead of Alembic migrations (see helpdesk/README.md TODOs).
    await create_all()
    yield


app = FastAPI(title="Global IT Helpdesk API", version="0.1.0", lifespan=lifespan)

app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(sla_policies.router)
app.include_router(tickets.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
