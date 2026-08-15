from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import SLAPolicy
from src.schemas import SLAPolicyCreate, SLAPolicyOut

router = APIRouter(prefix="/sla-policies", tags=["sla-policies"])


@router.post("", response_model=SLAPolicyOut, status_code=201)
async def create_sla_policy(payload: SLAPolicyCreate, db: AsyncSession = Depends(get_db)) -> SLAPolicy:
    policy = SLAPolicy(
        priority=payload.priority.value,
        response_minutes=payload.response_minutes,
        resolve_minutes=payload.resolve_minutes,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("", response_model=list[SLAPolicyOut])
async def list_sla_policies(db: AsyncSession = Depends(get_db)) -> list[SLAPolicy]:
    result = await db.scalars(select(SLAPolicy))
    return list(result.all())
