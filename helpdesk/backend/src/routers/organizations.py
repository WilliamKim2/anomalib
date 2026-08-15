from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Organization
from src.schemas import OrganizationCreate, OrganizationOut

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationOut, status_code=201)
async def create_organization(payload: OrganizationCreate, db: AsyncSession = Depends(get_db)) -> Organization:
    org = Organization(**payload.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("", response_model=list[OrganizationOut])
async def list_organizations(db: AsyncSession = Depends(get_db)) -> list[Organization]:
    result = await db.scalars(select(Organization))
    return list(result.all())
