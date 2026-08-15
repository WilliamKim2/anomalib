import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TicketType(str, enum.Enum):
    INCIDENT = "Incident"
    SERVICE_REQUEST = "ServiceRequest"
    PROBLEM = "Problem"
    CHANGE = "Change"


class TicketStatus(str, enum.Enum):
    NEW = "New"
    TRIAGED = "Triaged"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "InProgress"
    PENDING_CUSTOMER = "PendingCustomer"
    ESCALATED = "Escalated"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REOPENED = "Reopened"


class Priority(str, enum.Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class ImpactUrgency(str, enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# Impact x Urgency -> Priority, per docs/global-it-helpdesk-ticket-system-design.md section 4.3
PRIORITY_MATRIX: dict[tuple[ImpactUrgency, ImpactUrgency], Priority] = {
    (ImpactUrgency.HIGH, ImpactUrgency.HIGH): Priority.P1,
    (ImpactUrgency.HIGH, ImpactUrgency.MEDIUM): Priority.P2,
    (ImpactUrgency.HIGH, ImpactUrgency.LOW): Priority.P3,
    (ImpactUrgency.MEDIUM, ImpactUrgency.HIGH): Priority.P2,
    (ImpactUrgency.MEDIUM, ImpactUrgency.MEDIUM): Priority.P3,
    (ImpactUrgency.MEDIUM, ImpactUrgency.LOW): Priority.P4,
    (ImpactUrgency.LOW, ImpactUrgency.HIGH): Priority.P3,
    (ImpactUrgency.LOW, ImpactUrgency.MEDIUM): Priority.P4,
    (ImpactUrgency.LOW, ImpactUrgency.LOW): Priority.P4,
}

# Allowed status transitions, subset of the lifecycle in design doc section 5.
ALLOWED_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.NEW: {TicketStatus.TRIAGED, TicketStatus.ASSIGNED},
    TicketStatus.TRIAGED: {TicketStatus.ASSIGNED},
    TicketStatus.ASSIGNED: {TicketStatus.IN_PROGRESS},
    TicketStatus.IN_PROGRESS: {
        TicketStatus.PENDING_CUSTOMER,
        TicketStatus.ESCALATED,
        TicketStatus.RESOLVED,
    },
    TicketStatus.PENDING_CUSTOMER: {TicketStatus.IN_PROGRESS},
    TicketStatus.ESCALATED: {TicketStatus.IN_PROGRESS},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.REOPENED},
    TicketStatus.REOPENED: {TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: set(),
}


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20), default="Internal")  # Internal/Partner
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    region: Mapped[str] = mapped_column(String(20), default="APAC")

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(20), default="APAC")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    requester_type: Mapped[str] = mapped_column(String(20), default="Employee")  # Employee/Partner
    region: Mapped[str] = mapped_column(String(20), default="APAC")
    locale: Mapped[str] = mapped_column(String(10), default="ko-KR")
    role: Mapped[str] = mapped_column(String(20), default="Requester")
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True
    )

    organization: Mapped[Organization | None] = relationship(back_populates="users")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    priority: Mapped[str] = mapped_column(String(2), unique=True)
    response_minutes: Mapped[int] = mapped_column(Integer)
    resolve_minutes: Mapped[int] = mapped_column(Integer)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(20), default=TicketType.SERVICE_REQUEST.value)
    status: Mapped[str] = mapped_column(String(20), default=TicketStatus.NEW.value)
    priority: Mapped[str] = mapped_column(String(2))
    impact: Mapped[str] = mapped_column(String(10))
    urgency: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")

    requester_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    assignee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    team_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("teams.id"), nullable=True)
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)
    parent_ticket_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tickets.id"), nullable=True)

    source_channel: Mapped[str] = mapped_column(String(20), default="Portal")
    locale: Mapped[str] = mapped_column(String(10), default="ko-KR")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    sla_response_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_resolve_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id"), index=True)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id"), index=True)
    field: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    changed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
