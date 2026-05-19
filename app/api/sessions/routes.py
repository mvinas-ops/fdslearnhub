from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Schedule, ScheduleParticipant, SessionMaterialMapping, User
from app.schemas import ScheduleCreate, ScheduleUpdate, ParticipantIdsIn, AttendanceIn
from app.deps import get_current_user
from app.response import success_response, pagination_meta
from app.serializers import schedule_payload
from app.utils import page_params, clean_search, audit

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

def _can_manage(user: User) -> bool:
    return user.role in {"administrator", "admin", "cml", "community_leader"}

@router.get("")
async def list_sessions(page:int=1, limit:int=20, search:str|None=None, status:str|None=None, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not _can_manage(user):
        raise HTTPException(403, "Not allowed")
    page, limit = page_params(page, limit)
    q = select(Schedule).options(selectinload(Schedule.material), selectinload(Schedule.barangay), selectinload(Schedule.participants).selectinload(ScheduleParticipant.user))
    cq = select(func.count(Schedule.id))
    s = clean_search(search)
    if s:
        q = q.where(Schedule.session_title.ilike(f"%{s}%")); cq = cq.where(Schedule.session_title.ilike(f"%{s}%"))
    if status:
        q = q.where(Schedule.status == status); cq = cq.where(Schedule.status == status)
    total = await db.scalar(cq) or 0
    rows = (await db.execute(q.order_by(Schedule.session_date.desc()).offset((page-1)*limit).limit(limit))).scalars().unique().all()
    return success_response([await schedule_payload(db, r) for r in rows], meta=pagination_meta(page, limit, total))

@router.post("")
async def create_session(payload: ScheduleCreate, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not _can_manage(user):
        raise HTTPException(403, "Not allowed")
    s = Schedule(material_id=payload.material_id, session_title=payload.session_title, session_date=payload.date, session_time=payload.time, location=payload.location, barangay_id=payload.barangay_id, status="upcoming", created_by_id=user.id)
    db.add(s); await db.flush()
    for uid in payload.participant_ids:
        db.add(ScheduleParticipant(schedule_id=s.id, user_id=uid, attendance_status="pending"))
    if payload.material_id:
        db.add(SessionMaterialMapping(session_id=s.id, material_id=payload.material_id))
    await audit(db, user.id, "create", "sessions", s.id)
    await db.commit()
    return await get_session(s.id, db, user)

@router.get("/{session_id}")
async def get_session(session_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not _can_manage(user):
        raise HTTPException(403, "Not allowed")
    s = (await db.execute(select(Schedule).options(selectinload(Schedule.material), selectinload(Schedule.barangay), selectinload(Schedule.participants).selectinload(ScheduleParticipant.user)).where(Schedule.id == session_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Session not found")
    return success_response(await schedule_payload(db, s))

@router.put("/{session_id}")
async def update_session(session_id:int, payload:ScheduleUpdate, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not _can_manage(user):
        raise HTTPException(403, "Not allowed")
    s = await db.get(Schedule, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    data = payload.model_dump(exclude_unset=True)
    mapping = {"date":"session_date", "time":"session_time"}
    for k, v in data.items():
        if k == "participant_ids":
            continue
        setattr(s, mapping.get(k, k), v)
    if data.get("participant_ids") is not None:
        await db.execute(delete(ScheduleParticipant).where(ScheduleParticipant.schedule_id == s.id))
        for uid in data["participant_ids"]:
            db.add(ScheduleParticipant(schedule_id=s.id, user_id=uid, attendance_status="pending"))
    await audit(db, user.id, "update", "sessions", s.id)
    await db.commit()
    return await get_session(s.id, db, user)

@router.patch("/{session_id}/attendance")
async def mark_session_attendance(session_id:int, payload:AttendanceIn, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not _can_manage(user):
        raise HTTPException(403, "Not allowed")
    s = await db.get(Schedule, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    for item in payload.attendance:
        sp = (await db.execute(select(ScheduleParticipant).where(ScheduleParticipant.schedule_id == session_id, ScheduleParticipant.user_id == item.user_id))).scalar_one_or_none()
        if not sp:
            sp = ScheduleParticipant(schedule_id=session_id, user_id=item.user_id)
            db.add(sp)
        sp.attendance_status = item.status
    s.status = "completed"
    await audit(db, user.id, "attendance", "sessions", s.id)
    await db.commit()
    return success_response(None, "Attendance saved")

@router.delete("/{session_id}")
async def delete_session(session_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    if not _can_manage(user):
        raise HTTPException(403, "Not allowed")
    s = await db.get(Schedule, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    await db.delete(s)
    await audit(db, user.id, "delete", "sessions", session_id)
    await db.commit()
    return success_response(None, "Session deleted")
