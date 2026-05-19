from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import ClientGroup, ClientGroupMember, User, Barangay, CMLBarangay
from app.schemas import ClientGroupCreate, ClientGroupUpdate, ParticipantIdsIn
from app.deps import get_current_user
from app.response import success_response, pagination_meta
from app.utils import page_params, clean_search, audit

router = APIRouter(prefix="/api/client-groups", tags=["Client Groupings"])

def can_group(user: User) -> bool:
    return user.role in {"administrator", "admin", "cml", "community_leader"}

async def cml_allowed_barangays(db: AsyncSession, user: User) -> set[int] | None:
    if user.role in {"administrator", "admin"}:
        return None
    rows = await db.execute(select(CMLBarangay.barangay_id).where(CMLBarangay.cml_user_id == user.id))
    return set(rows.scalars().all())

async def assert_allowed(db: AsyncSession, actor: User, barangay_id: int | None, user_ids: list[int]):
    allowed = await cml_allowed_barangays(db, actor)
    if allowed is not None:
        if barangay_id is not None and barangay_id not in allowed:
            raise HTTPException(403, "Cannot create group outside assigned barangay")
        if user_ids:
            users = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
            if len(users) != len(set(user_ids)):
                raise HTTPException(404, "Some participants were not found")
            if any(u.barangay_id not in allowed for u in users):
                raise HTTPException(403, "Cannot group participants outside assigned barangays")

async def group_payload(db: AsyncSession, g: ClientGroup):
    members = getattr(g, "members", []) or []
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "status": g.status,
        "barangay": {"id": g.barangay.id, "name": g.barangay.name, "psgc": g.barangay.psgc} if g.barangay else None,
        "members_count": len(members),
        "members": [{"id": m.user.id, "full_name": m.user.full_name, "email": m.user.email, "status": m.user.status} for m in members if m.user],
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }

@router.get("")
async def list_client_groups(page:int=1, limit:int=20, search:str|None=None, barangay_id:int|None=None, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not can_group(user):
        raise HTTPException(403, "Not allowed")
    page, limit = page_params(page, limit)
    allowed = await cml_allowed_barangays(db, user)
    q = select(ClientGroup).options(selectinload(ClientGroup.barangay), selectinload(ClientGroup.members).selectinload(ClientGroupMember.user))
    cq = select(func.count(ClientGroup.id))
    if allowed is not None:
        q = q.where(ClientGroup.barangay_id.in_(allowed)); cq = cq.where(ClientGroup.barangay_id.in_(allowed))
    if barangay_id:
        q = q.where(ClientGroup.barangay_id == barangay_id); cq = cq.where(ClientGroup.barangay_id == barangay_id)
    s = clean_search(search)
    if s:
        q = q.where(ClientGroup.name.ilike(f"%{s}%")); cq = cq.where(ClientGroup.name.ilike(f"%{s}%"))
    total = await db.scalar(cq) or 0
    rows = (await db.execute(q.order_by(ClientGroup.id.desc()).offset((page-1)*limit).limit(limit))).scalars().unique().all()
    return success_response([await group_payload(db, g) for g in rows], meta=pagination_meta(page, limit, total))

@router.post("")
async def create_client_group(payload: ClientGroupCreate, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not can_group(user):
        raise HTTPException(403, "Not allowed")
    await assert_allowed(db, user, payload.barangay_id, payload.participant_ids)
    g = ClientGroup(name=payload.name, description=payload.description, barangay_id=payload.barangay_id, status=payload.status, created_by_id=user.id)
    db.add(g); await db.flush()
    for uid in payload.participant_ids:
        db.add(ClientGroupMember(group_id=g.id, user_id=uid))
    await audit(db, user.id, "create", "client_groups", g.id)
    await db.commit()
    return await get_client_group(g.id, db, user)

@router.get("/{group_id}")
async def get_client_group(group_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not can_group(user):
        raise HTTPException(403, "Not allowed")
    g = (await db.execute(select(ClientGroup).options(selectinload(ClientGroup.barangay), selectinload(ClientGroup.members).selectinload(ClientGroupMember.user)).where(ClientGroup.id == group_id))).scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Group not found")
    await assert_allowed(db, user, g.barangay_id, [])
    return success_response(await group_payload(db, g))

@router.put("/{group_id}")
async def update_client_group(group_id:int, payload:ClientGroupUpdate, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not can_group(user):
        raise HTTPException(403, "Not allowed")
    g = await db.get(ClientGroup, group_id)
    if not g:
        raise HTTPException(404, "Group not found")
    data = payload.model_dump(exclude_unset=True)
    new_barangay = data.get("barangay_id", g.barangay_id)
    new_members = data.get("participant_ids") or []
    await assert_allowed(db, user, new_barangay, new_members)
    for k in ["name", "description", "barangay_id", "status"]:
        if k in data:
            setattr(g, k, data[k])
    if data.get("participant_ids") is not None:
        await db.execute(delete(ClientGroupMember).where(ClientGroupMember.group_id == g.id))
        for uid in data["participant_ids"]:
            db.add(ClientGroupMember(group_id=g.id, user_id=uid))
    await audit(db, user.id, "update", "client_groups", g.id)
    await db.commit()
    return await get_client_group(g.id, db, user)

@router.post("/{group_id}/members")
async def add_members(group_id:int, payload:ParticipantIdsIn, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    g = await db.get(ClientGroup, group_id)
    if not g:
        raise HTTPException(404, "Group not found")
    await assert_allowed(db, user, g.barangay_id, payload.participant_ids)
    for uid in payload.participant_ids:
        exists = await db.scalar(select(ClientGroupMember.id).where(ClientGroupMember.group_id == group_id, ClientGroupMember.user_id == uid))
        if not exists:
            db.add(ClientGroupMember(group_id=group_id, user_id=uid))
    await db.commit()
    return success_response(None, "Members added")

@router.delete("/{group_id}")
async def delete_client_group(group_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    g = await db.get(ClientGroup, group_id)
    if not g:
        raise HTTPException(404, "Group not found")
    await assert_allowed(db, user, g.barangay_id, [])
    await db.delete(g)
    await audit(db, user.id, "delete", "client_groups", group_id)
    await db.commit()
    return success_response(None, "Group deleted")
