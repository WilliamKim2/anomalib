# Global IT Helpdesk — Backend (Phase 1 MVP)

Backend API slice for the ticket system described in
[`docs/global-it-helpdesk-ticket-system-design.md`](../docs/global-it-helpdesk-ticket-system-design.md).
This is the Phase 1 MVP scope from the design doc's roadmap (section 14): single-region ticket CRUD
with a basic SLA engine, simplified to one FastAPI service + one database (no microservices, no
Kafka) to keep the first iteration small.

## Stack

- FastAPI + SQLAlchemy (async) + Pydantic v2
- SQLite for local dev/tests by default, PostgreSQL via `docker/docker-compose.yml`

## Running locally

```bash
cd helpdesk/backend
pip install -e ".[dev]" 2>/dev/null || pip install -e . --group dev  # or: uv sync
uvicorn src.main:app --reload
```

API docs are served at `http://localhost:8000/docs` once running.

To run against PostgreSQL instead of the default SQLite file:

```bash
cd helpdesk/docker
docker compose up
```

## Running tests

```bash
cd helpdesk/backend
pytest
```

## What's implemented

- Domain model subset from the design doc's ERD (section 4.1): Organization, User, Team, Category,
  SLAPolicy, Ticket, TicketComment, TicketHistory
- Ticket creation with automatic priority derivation from the Impact × Urgency matrix (section 4.3)
- SLA response/resolve due-date calculation from `SLAPolicy` (flat offset — see TODO below)
- Ticket status lifecycle with transition validation (subset of section 5)
- Audit trail: status/assignee/team/priority changes are recorded in `TicketHistory`
- Comments (internal/external) on tickets

## Known simplifications / TODO (tracked against the design doc)

- **SLA calendar**: due dates are `created_at + offset`, ignoring team working-hours calendars and
  holidays (design doc section 6.1). Needs a calendar-aware scheduler before this is usable for real
  SLA reporting.
- **No auth/SSO**: endpoints are unauthenticated; `requester_id` / `changed_by_id` are passed as plain
  fields. SSO (SAML/OIDC) integration is a separate workstream (design doc section 2.2, 12).
- **No routing/rule engine, no Follow-the-Sun, no agentic AI layer** (design doc sections 9, 10) —
  out of scope for this slice.
- **Single region only**: no multi-cell deployment, no China cell (design doc sections 3.1, 3.3).
- **No intake channels wired up** (email/Slack/Teams/KakaoTalk/WeChat/WhatsApp, design doc section 8)
  — tickets are created directly via the API for now.
- **No Alembic migrations yet**: tables are created via `Base.metadata.create_all()` on startup for
  speed of iteration; switch to Alembic before this touches a real database with data worth preserving.
- **Ticket numbering** uses a row-count-based counter, which is not safe under concurrent writes;
  replace with a DB sequence before this runs with multiple workers.
