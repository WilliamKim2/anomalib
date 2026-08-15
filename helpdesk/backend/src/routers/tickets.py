from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Ticket, TicketComment, TicketHistory
from src.schemas import CommentCreate, CommentOut, HistoryOut, TicketCreate, TicketOut, TicketUpdate
from src.services import create_ticket, update_ticket

router = APIRouter(prefix="/tickets", tags=["tickets"])


async def _get_ticket_or_404(db: AsyncSession, ticket_id: str) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket_endpoint(payload: TicketCreate, db: AsyncSession = Depends(get_db)) -> Ticket:
    return await create_ticket(db, payload)


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    assignee_id: str | None = None,
    requester_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Ticket]:
    query = select(Ticket)
    if status is not None:
        query = query.where(Ticket.status == status)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
    if assignee_id is not None:
        query = query.where(Ticket.assignee_id == assignee_id)
    if requester_id is not None:
        query = query.where(Ticket.requester_id == requester_id)
    result = await db.scalars(query.order_by(Ticket.created_at.desc()))
    return list(result.all())


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)) -> Ticket:
    return await _get_ticket_or_404(db, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketOut)
async def patch_ticket(ticket_id: str, payload: TicketUpdate, db: AsyncSession = Depends(get_db)) -> Ticket:
    ticket = await _get_ticket_or_404(db, ticket_id)
    return await update_ticket(db, ticket, payload)


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(ticket_id: str, payload: CommentCreate, db: AsyncSession = Depends(get_db)) -> TicketComment:
    await _get_ticket_or_404(db, ticket_id)
    comment = TicketComment(ticket_id=ticket_id, **payload.model_dump())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
async def list_comments(ticket_id: str, db: AsyncSession = Depends(get_db)) -> list[TicketComment]:
    await _get_ticket_or_404(db, ticket_id)
    result = await db.scalars(
        select(TicketComment).where(TicketComment.ticket_id == ticket_id).order_by(TicketComment.created_at)
    )
    return list(result.all())


@router.get("/{ticket_id}/history", response_model=list[HistoryOut])
async def list_history(ticket_id: str, db: AsyncSession = Depends(get_db)) -> list[TicketHistory]:
    await _get_ticket_or_404(db, ticket_id)
    result = await db.scalars(
        select(TicketHistory).where(TicketHistory.ticket_id == ticket_id).order_by(TicketHistory.changed_at)
    )
    return list(result.all())
