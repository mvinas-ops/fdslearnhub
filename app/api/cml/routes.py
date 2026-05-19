import csv, io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import *
from app.schemas import ScheduleCreate, ScheduleUpdate, ParticipantIdsIn, AttendanceIn
from app.deps import require_cml
from app.response import success_response, pagination_meta
from app.serializers import user_payload, schedule_payload
from app.utils import clean_search, page_params, audit

router = APIRouter(prefix="/api/cml", tags=["CML"])

async def assigned_barangay_ids(db: AsyncSession, cml_id: int) -> set[int]:
    rows = await db.execute(select(CMLBarangay.barangay_id).where(CMLBarangay.cml_user_id == cml_id))
    return set(rows.scalars().all())

async def ensure_barangay_allowed(db: AsyncSession, cml: User, barangay_id: int):
    if barangay_id not in await assigned_barangay_ids(db, cml.id):
        raise HTTPException(403, "CML cannot manage this barangay")

async def ensure_participants_allowed(db: AsyncSession, cml: User, participant_ids: list[int]):
    allowed = await assigned_barangay_ids(db, cml.id)
    users = (await db.execute(select(User).where(User.id.in_(participant_ids)))).scalars().all() if participant_ids else []
    found = {u.id for u in users}
    missing = set(participant_ids) - found
    if missing:
        raise HTTPException(404, f"Participants not found: {sorted(missing)}")
    for u in users:
        if u.barangay_id not in allowed:
            raise HTTPException(403, "CML cannot manage participants outside assigned barangays")

@router.get("/assigned-barangays")
async def assigned_barangays(db: AsyncSession = Depends(get_db), cml: User = Depends(require_cml)):
    rows = (await db.execute(select(Barangay).join(CMLBarangay, CMLBarangay.barangay_id == Barangay.id).where(CMLBarangay.cml_user_id == cml.id))).scalars().all()
    return success_response([{"id": b.id, "name": b.name, "psgc": b.psgc} for b in rows])

@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), cml: User = Depends(require_cml)):
    ids = await assigned_barangay_ids(db, cml.id)
    if not ids:
        return success_response({"total_participants":0,"scheduled_sessions":0,"completed_sessions":0,"non_attendees":0,"overall_attendance_rate":0,"assigned_barangays":[]})
    total_participants = await db.scalar(select(func.count(User.id)).where(User.barangay_id.in_(ids), User.role == "trainee")) or 0
    scheduled = await db.scalar(select(func.count(Schedule.id)).where(Schedule.barangay_id.in_(ids), Schedule.status.in_(["upcoming","active"]))) or 0
    completed = await db.scalar(select(func.count(Schedule.id)).where(Schedule.barangay_id.in_(ids), Schedule.status == "completed")) or 0
    total_att = await db.scalar(select(func.count(ScheduleParticipant.id)).join(Schedule).where(Schedule.barangay_id.in_(ids))) or 0
    attended = await db.scalar(select(func.count(ScheduleParticipant.id)).join(Schedule).where(Schedule.barangay_id.in_(ids), ScheduleParticipant.attendance_status == "attended")) or 0
    absent = await db.scalar(select(func.count(ScheduleParticipant.id)).join(Schedule).where(Schedule.barangay_id.in_(ids), ScheduleParticipant.attendance_status == "absent")) or 0
    bgys = (await db.execute(select(Barangay).where(Barangay.id.in_(ids)))).scalars().all()
    return success_response({"total_participants":total_participants,"scheduled_sessions":scheduled,"completed_sessions":completed,"non_attendees":absent,"overall_attendance_rate":round((attended/total_att)*100) if total_att else 0,"assigned_barangays":[{"id":b.id,"name":b.name,"psgc":b.psgc} for b in bgys]})

@router.get("/participants")
async def participants(db: AsyncSession = Depends(get_db), cml: User = Depends(require_cml)):
    ids = await assigned_barangay_ids(db, cml.id)
    rows = (await db.execute(select(User).options(selectinload(User.role_obj),selectinload(User.barangay)).where(User.barangay_id.in_(ids), User.role == "trainee"))).scalars().all() if ids else []
    return success_response([await user_payload(db,u) for u in rows])

@router.get("/attendance-summary")
async def attendance_summary(db: AsyncSession = Depends(get_db), cml: User = Depends(require_cml)):
    ids = await assigned_barangay_ids(db, cml.id)
    total = await db.scalar(select(func.count(ScheduleParticipant.id)).join(Schedule).where(Schedule.barangay_id.in_(ids))) or 0
    attended = await db.scalar(select(func.count(ScheduleParticipant.id)).join(Schedule).where(Schedule.barangay_id.in_(ids), ScheduleParticipant.attendance_status == "attended")) or 0
    return success_response({"total": total, "attended": attended, "absent": max(total-attended,0), "attendance_rate": round((attended/total)*100) if total else 0})

@router.get("/schedules")
async def list_schedules(page:int=1, limit:int=20, search:str|None=None, status:str|None=None, barangay_id:int|None=None, db:AsyncSession=Depends(get_db), cml:User=Depends(require_cml)):
    page, limit = page_params(page, limit); ids = await assigned_barangay_ids(db,cml.id)
    if barangay_id:
        await ensure_barangay_allowed(db,cml,barangay_id); ids={barangay_id}
    q = select(Schedule).options(selectinload(Schedule.material),selectinload(Schedule.barangay),selectinload(Schedule.participants).selectinload(ScheduleParticipant.user).selectinload(User.barangay)).where(Schedule.barangay_id.in_(ids))
    cq = select(func.count(Schedule.id)).where(Schedule.barangay_id.in_(ids))
    s=clean_search(search)
    if s: q=q.where(Schedule.session_title.ilike(f"%{s}%")); cq=cq.where(Schedule.session_title.ilike(f"%{s}%"))
    if status: q=q.where(Schedule.status==status); cq=cq.where(Schedule.status==status)
    total=await db.scalar(cq) or 0
    rows=(await db.execute(q.order_by(Schedule.session_date.desc()).offset((page-1)*limit).limit(limit))).scalars().unique().all()
    return success_response([await schedule_payload(db,r) for r in rows], meta=pagination_meta(page,limit,total))

@router.get("/schedules/export-csv")
@router.get("/reports/attendance.csv")
async def attendance_csv(db:AsyncSession=Depends(get_db), cml:User=Depends(require_cml)):
    ids=await assigned_barangay_ids(db,cml.id)
    rows=(await db.execute(select(Schedule).options(selectinload(Schedule.barangay),selectinload(Schedule.participants).selectinload(ScheduleParticipant.user)).where(Schedule.barangay_id.in_(ids)))).scalars().unique().all()
    f=io.StringIO(); w=csv.writer(f); w.writerow(["schedule_id","session_title","date","barangay","participant","status"])
    for s in rows:
        for p in s.participants: w.writerow([s.id,s.session_title,s.session_date,s.barangay.name if s.barangay else "",p.user.full_name,p.attendance_status])
    f.seek(0); return StreamingResponse(iter([f.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=attendance.csv"})

@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id:int, db:AsyncSession=Depends(get_db), cml:User=Depends(require_cml)):
    s=(await db.execute(select(Schedule).options(selectinload(Schedule.material),selectinload(Schedule.barangay),selectinload(Schedule.participants).selectinload(ScheduleParticipant.user).selectinload(User.barangay)).where(Schedule.id==schedule_id))).scalar_one_or_none()
    if not s: raise HTTPException(404,"Schedule not found")
    await ensure_barangay_allowed(db,cml,s.barangay_id)
    return success_response(await schedule_payload(db,s))

@router.post("/schedules")
async def create_schedule(payload:ScheduleCreate, db:AsyncSession=Depends(get_db), cml:User=Depends(require_cml)):
    await ensure_barangay_allowed(db,cml,payload.barangay_id); await ensure_participants_allowed(db,cml,payload.participant_ids)
    s=Schedule(material_id=payload.material_id,session_title=payload.session_title,session_date=payload.date,session_time=payload.time,location=payload.location,barangay_id=payload.barangay_id,status="upcoming",created_by_id=cml.id)
    db.add(s); await db.flush()
    for uid in payload.participant_ids: db.add(ScheduleParticipant(schedule_id=s.id,user_id=uid,attendance_status="pending"))
    if payload.material_id: db.add(SessionMaterialMapping(session_id=s.id,material_id=payload.material_id))
    await audit(db,cml.id,"create","schedules",s.id); await db.commit(); return await get_schedule(s.id,db,cml)

@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id:int,payload:ScheduleUpdate,db:AsyncSession=Depends(get_db),cml:User=Depends(require_cml)):
    s=await db.get(Schedule,schedule_id)
    if not s: raise HTTPException(404,"Schedule not found")
    await ensure_barangay_allowed(db,cml,s.barangay_id)
    data=payload.model_dump(exclude_unset=True)
    if "barangay_id" in data and data["barangay_id"]: await ensure_barangay_allowed(db,cml,data["barangay_id"]); s.barangay_id=data["barangay_id"]
    mapping={"date":"session_date","time":"session_time"}
    for k,v in data.items():
        if k in ["participant_ids","barangay_id"]: continue
        setattr(s,mapping.get(k,k),v)
    if data.get("participant_ids") is not None:
        await ensure_participants_allowed(db,cml,data["participant_ids"])
        await db.execute(delete(ScheduleParticipant).where(ScheduleParticipant.schedule_id==s.id))
        for uid in data["participant_ids"]: db.add(ScheduleParticipant(schedule_id=s.id,user_id=uid,attendance_status="pending"))
    await audit(db,cml.id,"update","schedules",s.id); await db.commit(); return await get_schedule(s.id,db,cml)

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id:int,db:AsyncSession=Depends(get_db),cml:User=Depends(require_cml)):
    s=await db.get(Schedule,schedule_id)
    if not s: raise HTTPException(404,"Schedule not found")
    await ensure_barangay_allowed(db,cml,s.barangay_id)
    await db.delete(s); await audit(db,cml.id,"delete","schedules",schedule_id); await db.commit(); return success_response(None,"Schedule deleted")

@router.post("/schedules/{schedule_id}/participants")
async def add_participants(schedule_id:int,payload:ParticipantIdsIn,db:AsyncSession=Depends(get_db),cml:User=Depends(require_cml)):
    s=await db.get(Schedule,schedule_id)
    if not s: raise HTTPException(404,"Schedule not found")
    await ensure_barangay_allowed(db,cml,s.barangay_id); await ensure_participants_allowed(db,cml,payload.participant_ids)
    for uid in payload.participant_ids:
        if not await db.scalar(select(ScheduleParticipant.id).where(ScheduleParticipant.schedule_id==schedule_id,ScheduleParticipant.user_id==uid)):
            db.add(ScheduleParticipant(schedule_id=schedule_id,user_id=uid,attendance_status="pending"))
    await db.commit(); return success_response(None,"Participants added")

@router.delete("/schedules/{schedule_id}/participants/{user_id}")
async def remove_participant(schedule_id:int,user_id:int,db:AsyncSession=Depends(get_db),cml:User=Depends(require_cml)):
    s=await db.get(Schedule,schedule_id)
    if not s: raise HTTPException(404,"Schedule not found")
    await ensure_barangay_allowed(db,cml,s.barangay_id)
    await db.execute(delete(ScheduleParticipant).where(ScheduleParticipant.schedule_id==schedule_id,ScheduleParticipant.user_id==user_id)); await db.commit(); return success_response(None,"Participant removed")

@router.patch("/schedules/{schedule_id}/attendance")
async def mark_attendance(schedule_id:int,payload:AttendanceIn,db:AsyncSession=Depends(get_db),cml:User=Depends(require_cml)):
    s=await db.get(Schedule,schedule_id)
    if not s: raise HTTPException(404,"Schedule not found")
    await ensure_barangay_allowed(db,cml,s.barangay_id); await ensure_participants_allowed(db,cml,[a.user_id for a in payload.attendance])
    for item in payload.attendance:
        sp=(await db.execute(select(ScheduleParticipant).where(ScheduleParticipant.schedule_id==schedule_id,ScheduleParticipant.user_id==item.user_id))).scalar_one_or_none()
        if not sp:
            sp=ScheduleParticipant(schedule_id=schedule_id,user_id=item.user_id); db.add(sp)
        sp.attendance_status=item.status
    s.status="completed"
    await audit(db,cml.id,"attendance","schedules",s.id); await db.commit(); return success_response(None,"Attendance updated")
