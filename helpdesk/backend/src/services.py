from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    ALLOWED_TRANSITIONS,
    PRIORITY_MATRIX,
    ImpactUrgency,
    SLAPolicy,
    Ticket,
    TicketHistory,
    TicketStatus,
)
from src.schemas import TicketCreate, TicketUpdate


def compute_priority(impact: ImpactUrgency, urgency: ImpactUrgency) -> str:
    """Impact x Urgency matrix, see docs/global-it-helpdesk-ticket-system-design.md section 4.3."""
    return PRIORITY_MATRIX[(impact, urgency)].value


async def _next_ticket_number(db: AsyncSession) -> str:
    count = await db.scalar(select(func.count()).select_from(Ticket))
    return f"TCK-{(count or 0) + 1:06d}"


async def create_ticket(db: AsyncSession, payload: TicketCreate) -> Ticket:
    priority = compute_priority(payload.impact, payload.urgency)

    sla_policy = await db.scalar(select(SLAPolicy).where(SLAPolicy.priority == priority))
    now = datetime.utcnow()
    # NOTE: MVP simplification - due dates use a flat offset from creation time.
    # Production must compute against each team's working-hours calendar (design doc section 6.1).
    response_due = now + timedelta(minutes=sla_policy.response_minutes) if sla_policy else None
    resolve_due = now + timedelta(minutes=sla_policy.resolve_minutes) if sla_policy else None

    ticket = Ticket(
        ticket_number=await _next_ticket_number(db),
        type=payload.type.value,
        status=TicketStatus.NEW.value,
        priority=priority,
        impact=payload.impact.value,
        urgency=payload.urgency.value,
        title=payload.title,
        description=payload.description,
        requester_id=payload.requester_id,
        category_id=payload.category_id,
        team_id=payload.team_id,
        source_channel=payload.source_channel,
        locale=payload.locale,
        sla_response_due=response_due,
        sla_resolve_due=resolve_due,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def _record_history(
    db: AsyncSession, ticket_id: str, field: str, old_value: str | None, new_value: str | None, changed_by_id: str | None
) -> None:
    if old_value == new_value:
        return
    db.add(
        TicketHistory(
            ticket_id=ticket_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            changed_by_id=changed_by_id,
        )
    )


async def update_ticket(db: AsyncSession, ticket: Ticket, payload: TicketUpdate) -> Ticket:
    if payload.status is not None and payload.status.value != ticket.status:
        current = TicketStatus(ticket.status)
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if payload.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot transition ticket from {current.value} to {payload.status.value}",
            )
        await _record_history(db, ticket.id, "status", ticket.status, payload.status.value, payload.changed_by_id)
        ticket.status = payload.status.value
        if payload.status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.utcnow()
        if payload.status == TicketStatus.CLOSED:
            ticket.closed_at = datetime.utcnow()

    if payload.assignee_id is not None and payload.assignee_id != ticket.assignee_id:
        await _record_history(db, ticket.id, "assignee_id", ticket.assignee_id, payload.assignee_id, payload.changed_by_id)
        ticket.assignee_id = payload.assignee_id

    if payload.team_id is not None and payload.team_id != ticket.team_id:
        await _record_history(db, ticket.id, "team_id", ticket.team_id, payload.team_id, payload.changed_by_id)
        ticket.team_id = payload.team_id

    if payload.priority is not None and payload.priority.value != ticket.priority:
        await _record_history(db, ticket.id, "priority", ticket.priority, payload.priority.value, payload.changed_by_id)
        ticket.priority = payload.priority.value

    await db.commit()
    await db.refresh(ticket)
    return ticket
