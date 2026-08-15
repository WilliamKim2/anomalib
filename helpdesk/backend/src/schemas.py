from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from src.models import ImpactUrgency, Priority, TicketStatus, TicketType


class OrganizationCreate(BaseModel):
    name: str
    type: str = "Internal"
    country: str | None = None
    region: str = "APAC"


class OrganizationOut(OrganizationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    requester_type: str = "Employee"
    region: str = "APAC"
    locale: str = "ko-KR"
    role: str = "Requester"
    organization_id: str | None = None


class UserOut(UserCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class CategoryCreate(BaseModel):
    name: str
    parent_id: str | None = None


class CategoryOut(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class SLAPolicyCreate(BaseModel):
    priority: Priority
    response_minutes: int
    resolve_minutes: int


class SLAPolicyOut(SLAPolicyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class TicketCreate(BaseModel):
    title: str
    description: str = ""
    type: TicketType = TicketType.SERVICE_REQUEST
    impact: ImpactUrgency
    urgency: ImpactUrgency
    requester_id: str
    category_id: str | None = None
    team_id: str | None = None
    source_channel: str = "Portal"
    locale: str = "ko-KR"


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    assignee_id: str | None = None
    team_id: str | None = None
    priority: Priority | None = None
    changed_by_id: str | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_number: str
    type: str
    status: str
    priority: str
    impact: str
    urgency: str
    title: str
    description: str
    requester_id: str
    assignee_id: str | None
    team_id: str | None
    category_id: str | None
    parent_ticket_id: str | None
    source_channel: str
    locale: str
    created_at: datetime
    updated_at: datetime
    sla_response_due: datetime | None
    sla_resolve_due: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None


class CommentCreate(BaseModel):
    author_id: str
    body: str
    is_internal: bool = False


class CommentOut(CommentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ticket_id: str
    created_at: datetime


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ticket_id: str
    field: str
    old_value: str | None
    new_value: str | None
    changed_by_id: str | None
    changed_at: datetime
