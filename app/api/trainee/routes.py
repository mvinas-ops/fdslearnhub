from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import *
from app.deps import require_trainee, get_current_user
from app.response import success_response
from app.serializers import user_payload, material_payload, lesson_payload, schedule_payload
from app.utils import user_unlocked_material_ids, material_progress

router = APIRouter(prefix="/api/trainee", tags=["Trainee"])

@router.get("/profile")
async def profile(db:AsyncSession=Depends(get_db), user:User=Depends(require_trainee)):
    data=await user_payload(db,user)
    unlocked=await user_unlocked_material_ids(db,user.id)
    progresses=[await material_progress(db,user.id,mid) for mid in unlocked]
    data.update({"materials_available_count":len(unlocked),"average_progress":round(sum(progresses)/len(progresses)) if progresses else 0})
    return success_response(data)

@router.get("/sessions")
async def sessions(db:AsyncSession=Depends(get_db), user:User=Depends(require_trainee)):
    rows=(await db.execute(select(Schedule).options(selectinload(Schedule.participants).selectinload(ScheduleParticipant.user),selectinload(Schedule.material),selectinload(Schedule.barangay)).join(ScheduleParticipant).where(ScheduleParticipant.user_id==user.id).order_by(Schedule.session_date.desc()))).scalars().unique().all()
    return success_response([await schedule_payload(db,s) for s in rows])

@router.get("/materials")
async def materials(db:AsyncSession=Depends(get_db), user:User=Depends(require_trainee)):
    ids=await user_unlocked_material_ids(db,user.id)
    if not ids: return success_response([])
    rows=(await db.execute(select(TrainingMaterial).where(TrainingMaterial.id.in_(ids), TrainingMaterial.status=="active"))).scalars().all()
    return success_response([await material_payload(db,m,user.id) for m in rows])

@router.get("/materials/{material_id}")
async def material_detail(material_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(require_trainee)):
    if material_id not in await user_unlocked_material_ids(db,user.id): raise HTTPException(403,"Material is locked")
    m=await db.get(TrainingMaterial, material_id)
    if not m: raise HTTPException(404,"Material not found")
    data=await material_payload(db,m,user.id)
    lessons=(await db.execute(select(Lesson).where(Lesson.material_id==material_id).order_by(Lesson.order_index))).scalars().all()
    resources=(await db.execute(select(Resource).options(selectinload(Resource.uploaded_by)).where(Resource.material_id==material_id))).scalars().all()
    from app.serializers import resource_payload
    data["lessons"]=[await lesson_payload(db,l,user.id) for l in lessons]
    data["resources"]=[resource_payload(r) for r in resources]
    return success_response(data)

@router.get("/materials/{material_id}/progress")
async def material_progress_route(material_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(require_trainee)):
    if material_id not in await user_unlocked_material_ids(db,user.id): raise HTTPException(403,"Material is locked")
    return success_response({"material_id":material_id,"progress":await material_progress(db,user.id,material_id)})

@router.patch("/lessons/{lesson_id}/complete")
async def complete_lesson(lesson_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(require_trainee)):
    lesson=await db.get(Lesson,lesson_id)
    if not lesson: raise HTTPException(404,"Lesson not found")
    if lesson.material_id not in await user_unlocked_material_ids(db,user.id): raise HTTPException(403,"Material is locked")
    progress=(await db.execute(select(LessonProgress).where(LessonProgress.user_id==user.id, LessonProgress.lesson_id==lesson_id))).scalar_one_or_none()
    if not progress:
        progress=LessonProgress(user_id=user.id,lesson_id=lesson_id,is_completed=True,completed_at=datetime.utcnow()); db.add(progress)
    else:
        progress.is_completed=True; progress.completed_at=datetime.utcnow()
    await db.commit(); return success_response(await lesson_payload(db,lesson,user.id),"Lesson completed")
