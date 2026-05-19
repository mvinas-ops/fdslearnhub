from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Role, TrainingMaterial, Lesson, Resource, Schedule, ScheduleParticipant, SessionMaterialMapping
from .utils import dt_to_iso, material_progress

def role_payload(role: Role, user_count: int = 0):
    return {
        "id": role.id,
        "name": role.name,
        "slug": role.slug,
        "description": role.description,
        "color": role.color,
        "is_system_role": role.is_system_role,
        "user_count": user_count,
        "permissions": [rp.permission.key for rp in role.permissions if rp.permission],
    }

async def user_payload(db: AsyncSession, user: User):
    sessions_count = await db.scalar(
        select(func.count(ScheduleParticipant.id)).where(ScheduleParticipant.user_id == user.id, ScheduleParticipant.attendance_status == "attended")
    ) or 0
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role_obj.slug if user.role_obj else user.role,
        "role_name": user.role_obj.name if user.role_obj else user.role,
        "barangay": {"id": user.barangay.id, "name": user.barangay.name, "psgc": user.barangay.psgc} if user.barangay else None,
        "status": user.status,
        "joined_date": dt_to_iso(user.created_at),
        "phone": user.phone,
        "psgc": user.psgc,
        "sessions_attended_count": sessions_count,
    }

async def material_payload(db: AsyncSession, material: TrainingMaterial, user_id: int | None = None):
    lesson_count = await db.scalar(select(func.count(Lesson.id)).where(Lesson.material_id == material.id)) or 0
    resource_count = await db.scalar(select(func.count(Resource.id)).where(Resource.material_id == material.id)) or 0
    data = {
        "id": material.id,
        "title": material.title,
        "slug": material.slug,
        "description": material.description,
        "category": material.category,
        "status": material.status,
        "lesson_count": lesson_count,
        "resource_count": resource_count,
        "number_of_lessons": material.number_of_lessons,
        "total_duration": material.total_duration,
        "created_at": dt_to_iso(material.created_at),
        "updated_at": dt_to_iso(material.updated_at),
    }
    if user_id:
        data["progress"] = await material_progress(db, user_id, material.id)
    return data

async def lesson_payload(db: AsyncSession, lesson: Lesson, user_id: int | None = None):
    completed = False
    if user_id:
        from .models import LessonProgress
        completed = bool(await db.scalar(select(LessonProgress.is_completed).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson.id)))
    return {
        "id": lesson.id,
        "material_id": lesson.material_id,
        "lesson_number": lesson.lesson_number,
        "title": lesson.title,
        "duration_minutes": lesson.duration_minutes,
        "order_index": lesson.order_index,
        "is_completed": completed,
    }

def resource_payload(resource: Resource):
    return {
        "id": resource.id,
        "material_id": resource.material_id,
        "file_name": resource.file_name,
        "file_type": resource.file_type,
        "file_size": resource.file_size,
        "download_url": f"/api/resources/{resource.id}/download",
        "uploaded_by": resource.uploaded_by.full_name if resource.uploaded_by else None,
        "created_at": dt_to_iso(resource.created_at),
    }

async def schedule_payload(db: AsyncSession, sched: Schedule):
    total = await db.scalar(select(func.count(ScheduleParticipant.id)).where(ScheduleParticipant.schedule_id == sched.id)) or 0
    attended = await db.scalar(select(func.count(ScheduleParticipant.id)).where(ScheduleParticipant.schedule_id == sched.id, ScheduleParticipant.attendance_status == "attended")) or 0
    participants = []
    for sp in sched.participants:
        participants.append({
            "id": sp.user.id,
            "full_name": sp.user.full_name,
            "email": sp.user.email,
            "barangay": sp.user.barangay.name if sp.user.barangay else None,
            "attendance_status": sp.attendance_status,
        })
    return {
        "id": sched.id,
        "material": {"id": sched.material.id, "title": sched.material.title, "slug": sched.material.slug} if sched.material else None,
        "session_title": sched.session_title,
        "date": sched.session_date.isoformat(),
        "time": sched.session_time,
        "location": sched.location,
        "barangay": {"id": sched.barangay.id, "name": sched.barangay.name, "psgc": sched.barangay.psgc} if sched.barangay else None,
        "status": sched.status,
        "participants": participants,
        "participants_count": total,
        "attended_count": attended,
        "attendance_rate": round((attended / total) * 100) if total else 0,
    }
