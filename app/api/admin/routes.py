import csv, io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import *
from app.schemas import *
from app.auth import hash_password
from app.deps import require_admin, get_current_user
from app.response import success_response, pagination_meta
from app.serializers import user_payload, role_payload, material_payload
from app.utils import clean_search, normalize_slug, page_params, audit

router = APIRouter(prefix="/api/admin", tags=["Admin"])

async def set_role_permissions(db, role, keys):
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    if keys:
        rows = (await db.execute(select(Permission).where(Permission.key.in_(keys)))).scalars().all()
        found = {p.key for p in rows}
        missing = set(keys) - found
        if missing:
            raise HTTPException(400, f"Unknown permission keys: {sorted(missing)}")
        for p in rows:
            db.add(RolePermission(role_id=role.id, permission_id=p.id))

@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    total_users = await db.scalar(select(func.count(User.id))) or 0
    active_sessions = await db.scalar(select(func.count(Schedule.id)).where(Schedule.status.in_(["upcoming","active"]))) or 0
    materials = await db.scalar(select(func.count(TrainingMaterial.id))) or 0
    total_lessons = await db.scalar(select(func.count(LessonProgress.id))) or 0
    completed = await db.scalar(select(func.count(LessonProgress.id)).where(LessonProgress.is_completed == True)) or 0
    rate = round((completed/total_lessons)*100) if total_lessons else 0
    return success_response({"total_users": total_users, "active_sessions": active_sessions, "training_materials": materials, "completion_rate": rate, "recent_activity": []})

@router.get("/users")
async def list_users(page:int=1, limit:int=20, search:str|None=None, role:str|None=None, status:str|None=None, barangay:int|None=None, db:AsyncSession=Depends(get_db), _:User=Depends(require_admin)):
    page, limit = page_params(page, limit); q=select(User).options(selectinload(User.role_obj), selectinload(User.barangay)); cq=select(func.count(User.id))
    filters=[]; s=clean_search(search)
    if s: filters.append(or_(User.full_name.ilike(f"%{s}%"), User.email.ilike(f"%{s}%")))
    if role: filters.append(User.role == role)
    if status: filters.append(User.status == status)
    if barangay: filters.append(User.barangay_id == barangay)
    for f in filters: q=q.where(f); cq=cq.where(f)
    total=await db.scalar(cq) or 0
    rows=(await db.execute(q.order_by(User.id).offset((page-1)*limit).limit(limit))).scalars().all()
    return success_response([await user_payload(db,u) for u in rows], meta=pagination_meta(page,limit,total))

@router.get("/users/{user_id}")
async def get_user(user_id:int, db:AsyncSession=Depends(get_db), _:User=Depends(require_admin)):
    u=(await db.execute(select(User).options(selectinload(User.role_obj), selectinload(User.barangay)).where(User.id==user_id))).scalar_one_or_none()
    if not u: raise HTTPException(404,"User not found")
    return success_response(await user_payload(db,u))

@router.post("/users")
async def create_user(payload:UserCreate, db:AsyncSession=Depends(get_db), actor:User=Depends(require_admin)):
    role=await db.get(Role,payload.role_id)
    if not role:
        raise HTTPException(400,"Invalid role_id")

    email = payload.email.lower().strip()
    if await db.scalar(select(User.id).where(func.lower(User.email)==email)):
        raise HTTPException(409,"Email already exists")

    if payload.barangay_id and not await db.get(Barangay, payload.barangay_id):
        raise HTTPException(400,"Invalid barangay_id")

    # Validate assigned sessions before insert, so bad IDs do not become FK 500s.
    for sid in payload.session_ids:
        if not await db.get(Schedule, sid):
            raise HTTPException(400, f"Invalid session_id: {sid}")

    u=User(
        full_name=payload.full_name,
        email=email,
        password=hash_password(payload.password),
        role=role.slug,
        role_id=role.id,
        barangay_id=payload.barangay_id,
        phone=payload.phone,
        psgc=payload.psgc,
        status=payload.status,
        is_active=payload.status=="active",
    )
    db.add(u)
    try:
        await db.flush()
        user_id = u.id
        for sid in payload.session_ids:
            db.add(UserSession(user_id=user_id,schedule_id=sid,status="assigned"))
        await audit(db,actor.id,"create","users",user_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409,"Email already exists")

    loaded=(await db.execute(
        select(User)
        .options(selectinload(User.role_obj), selectinload(User.barangay))
        .where(User.id==user_id)
    )).scalar_one()
    return success_response(await user_payload(db,loaded),"User created")

@router.put("/users/{user_id}")
async def update_user(user_id:int,payload:UserUpdate,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    u=await db.get(User,user_id); 
    if not u: raise HTTPException(404,"User not found")
    data=payload.model_dump(exclude_unset=True)
    if "role_id" in data and data["role_id"]:
        role=await db.get(Role,data["role_id"]); 
        if not role: raise HTTPException(400,"Invalid role_id")
        u.role_id=role.id; u.role=role.slug
    if "password" in data and data["password"]: u.password=hash_password(data.pop("password"))
    for k in ["full_name","email","barangay_id","phone","psgc","status"]:
        if k in data: setattr(u,k,data[k])
    if u.status: u.is_active = u.status == "active"
    if data.get("session_ids") is not None:
        await db.execute(delete(UserSession).where(UserSession.user_id==u.id))
        for sid in data["session_ids"]: db.add(UserSession(user_id=u.id,schedule_id=sid,status="assigned"))
    try:
        await audit(db,actor.id,"update","users",u.id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409,"Email already exists")
    loaded=(await db.execute(select(User).options(selectinload(User.role_obj), selectinload(User.barangay)).where(User.id==user_id))).scalar_one()
    return success_response(await user_payload(db,loaded),"User updated")

@router.patch("/users/{user_id}/status")
async def user_status(user_id:int,payload:StatusIn,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    u=await db.get(User,user_id); 
    if not u: raise HTTPException(404,"User not found")
    u.status=payload.status; u.is_active=payload.status=="active"; await audit(db,actor.id,"status","users",u.id); await db.commit()
    loaded=(await db.execute(select(User).options(selectinload(User.role_obj), selectinload(User.barangay)).where(User.id==user_id))).scalar_one()
    return success_response(await user_payload(db,loaded))

@router.delete("/users/{user_id}")
async def delete_user(user_id:int,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    u=await db.get(User,user_id); 
    if not u: raise HTTPException(404,"User not found")
    await db.delete(u); await audit(db,actor.id,"delete","users",user_id); await db.commit(); return success_response(None,"User deleted")

@router.post("/users/{user_id}/sessions")
async def add_user_sessions(user_id:int,payload:SessionIdsIn,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    for sid in payload.session_ids:
        if not await db.scalar(select(UserSession.id).where(UserSession.user_id==user_id, UserSession.schedule_id==sid)):
            db.add(UserSession(user_id=user_id,schedule_id=sid,status="assigned"))
    await db.commit(); return success_response(None,"Sessions assigned")

@router.delete("/users/{user_id}/sessions/{session_id}")
async def remove_user_session(user_id:int,session_id:int,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    await db.execute(delete(UserSession).where(UserSession.user_id==user_id,UserSession.schedule_id==session_id)); await db.commit(); return success_response(None,"Session removed")

@router.get("/permissions")
async def permissions(db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    rows=(await db.execute(select(Permission).order_by(Permission.key))).scalars().all(); return success_response([{"id":p.id,"key":p.key,"name":p.name,"module":p.module} for p in rows])

@router.get("/roles")
async def roles(db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    rows=(await db.execute(select(Role).options(selectinload(Role.permissions).selectinload(RolePermission.permission)).order_by(Role.id))).scalars().all(); out=[]
    for r in rows: out.append(role_payload(r, await db.scalar(select(func.count(User.id)).where(User.role_id==r.id)) or 0))
    return success_response(out)

@router.get("/roles/{role_id}")
async def get_role(role_id:int,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    r=(await db.execute(select(Role).options(selectinload(Role.permissions).selectinload(RolePermission.permission)).where(Role.id==role_id))).scalar_one_or_none()
    if not r: raise HTTPException(404,"Role not found")
    return success_response(role_payload(r, await db.scalar(select(func.count(User.id)).where(User.role_id==r.id)) or 0))

@router.post("/roles")
async def create_role(payload:RoleCreate,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    slug=normalize_slug(payload.name).replace('-','_')
    exists = await db.scalar(select(Role.id).where(or_(Role.slug == slug, Role.name == payload.name)))
    if exists:
        raise HTTPException(409,"Role already exists")
    r=Role(name=payload.name,slug=slug,description=payload.description,color=payload.color,is_system_role=False)
    db.add(r)
    try:
        await db.flush()
        await set_role_permissions(db,r,payload.permission_keys)
        await audit(db,actor.id,"create","roles",r.id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409,"Role already exists")
    except Exception:
        await db.rollback()
        raise
    loaded=(await db.execute(
        select(Role)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        .where(Role.id==r.id)
    )).scalar_one()
    return success_response(role_payload(loaded),"Role created")

@router.put("/roles/{role_id}")
async def update_role(role_id:int,payload:RoleUpdate,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    r=await db.get(Role,role_id); 
    if not r: raise HTTPException(404,"Role not found")
    data=payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != r.name:
        slug=normalize_slug(data["name"]).replace('-','_')
        if await db.scalar(select(Role.id).where(or_(Role.slug == slug, Role.name == data["name"]), Role.id != role_id)):
            raise HTTPException(409,"Role already exists")
        r.slug=slug
    for k in ["name","description","color"]:
        if k in data: setattr(r,k,data[k])
    if "permission_keys" in data: await set_role_permissions(db,r,data["permission_keys"])
    try:
        await audit(db,actor.id,"update","roles",r.id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409,"Role already exists")
    loaded=(await db.execute(
        select(Role)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        .where(Role.id==role_id)
    )).scalar_one()
    return success_response(role_payload(loaded),"Role updated")

@router.delete("/roles/{role_id}")
async def delete_role(role_id:int,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    r=await db.get(Role,role_id); 
    if not r: raise HTTPException(404,"Role not found")
    if r.is_system_role: raise HTTPException(400,"System roles cannot be deleted")
    await db.delete(r); await audit(db,actor.id,"delete","roles",role_id); await db.commit(); return success_response(None,"Role deleted")

@router.get("/materials")
async def list_materials(page:int=1,limit:int=20,search:str|None=None,category:str|None=None,status:str|None=None,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    page,limit=page_params(page,limit); q=select(TrainingMaterial); cq=select(func.count(TrainingMaterial.id)); filters=[]; s=clean_search(search)
    if s: filters.append(TrainingMaterial.title.ilike(f"%{s}%"))
    if category: filters.append(TrainingMaterial.category==category)
    if status: filters.append(TrainingMaterial.status==status)
    for f in filters: q=q.where(f); cq=cq.where(f)
    rows=(await db.execute(q.order_by(TrainingMaterial.id).offset((page-1)*limit).limit(limit))).scalars().all(); total=await db.scalar(cq) or 0
    return success_response([await material_payload(db,m) for m in rows], meta=pagination_meta(page,limit,total))

@router.get("/materials/{material_id}")
async def get_material(material_id:int,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    m=await db.get(TrainingMaterial,material_id); 
    if not m: raise HTTPException(404,"Material not found")
    return success_response(await material_payload(db,m))

@router.post("/materials")
async def create_material(payload:MaterialCreate,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    base=normalize_slug(payload.title); slug=base; i=2
    while await db.scalar(select(TrainingMaterial.id).where(TrainingMaterial.slug==slug)): slug=f"{base}-{i}"; i+=1
    m=TrainingMaterial(**payload.model_dump(),slug=slug,created_by_id=actor.id); db.add(m); await audit(db,actor.id,"create","materials",None); await db.commit(); await db.refresh(m); return success_response(await material_payload(db,m),"Material created")

@router.put("/materials/{material_id}")
async def update_material(material_id:int,payload:MaterialUpdate,db:AsyncSession=Depends(get_db),actor:User=Depends(require_admin)):
    m=await db.get(TrainingMaterial,material_id); 
    if not m: raise HTTPException(404,"Material not found")
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(m,k,v)
    if payload.title: m.slug=normalize_slug(payload.title)
    await audit(db,actor.id,"update","materials",m.id); await db.commit(); return success_response(await material_payload(db,m),"Material updated")

@router.patch("/materials/{material_id}/status")
async def material_status(material_id:int,payload:StatusIn,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    m=await db.get(TrainingMaterial,material_id); 
    if not m: raise HTTPException(404,"Material not found")
    m.status=payload.status; await db.commit(); return success_response(await material_payload(db,m))

@router.delete("/materials/{material_id}")
async def delete_material(material_id:int,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    m=await db.get(TrainingMaterial,material_id); 
    if not m: raise HTTPException(404,"Material not found")
    await db.delete(m); await db.commit(); return success_response(None,"Material deleted")

@router.post("/materials/{material_id}/lessons")
async def create_lesson(material_id:int,payload:LessonCreate,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    if not await db.get(TrainingMaterial,material_id): raise HTTPException(404,"Material not found")
    l=Lesson(material_id=material_id,**payload.model_dump()); db.add(l); await db.commit(); await db.refresh(l); return success_response({"id":l.id},"Lesson created")

@router.put("/lessons/{lesson_id}")
async def update_lesson(lesson_id:int,payload:LessonUpdate,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    l=await db.get(Lesson,lesson_id); 
    if not l: raise HTTPException(404,"Lesson not found")
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(l,k,v)
    await db.commit(); return success_response({"id":l.id},"Lesson updated")

@router.delete("/lessons/{lesson_id}")
async def delete_lesson(lesson_id:int,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    l=await db.get(Lesson,lesson_id); 
    if not l: raise HTTPException(404,"Lesson not found")
    await db.delete(l); await db.commit(); return success_response(None,"Lesson deleted")

@router.get("/session-material-mappings")
async def mappings(db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    rows=(await db.execute(select(SessionMaterialMapping).options(selectinload(SessionMaterialMapping.schedule), selectinload(SessionMaterialMapping.material)).order_by(SessionMaterialMapping.session_id))).scalars().all()
    return success_response([{"id":r.id,"session_id":r.session_id,"session_title":r.schedule.session_title if r.schedule else None,"material":{"id":r.material.id,"title":r.material.title} if r.material else None} for r in rows])

@router.post("/session-material-mappings")
async def create_mapping(payload:MappingCreate,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    created=[]
    for mid in payload.material_ids:
        if not await db.scalar(select(SessionMaterialMapping.id).where(SessionMaterialMapping.session_id==payload.session_id,SessionMaterialMapping.material_id==mid)):
            obj=SessionMaterialMapping(session_id=payload.session_id,material_id=mid); db.add(obj); await db.flush(); created.append(obj.id)
    await db.commit(); return success_response({"created_ids":created},"Mapping saved")

@router.put("/session-material-mappings/{mapping_id}")
async def update_mapping(mapping_id:int,payload:MappingUpdate,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    m=await db.get(SessionMaterialMapping,mapping_id); 
    if not m: raise HTTPException(404,"Mapping not found")
    if payload.session_id: m.session_id=payload.session_id
    if payload.material_ids: m.material_id=payload.material_ids[0]
    await db.commit(); return success_response({"id":m.id},"Mapping updated")

@router.delete("/session-material-mappings/{mapping_id}")
async def delete_mapping(mapping_id:int,db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    m=await db.get(SessionMaterialMapping,mapping_id); 
    if not m: raise HTTPException(404,"Mapping not found")
    await db.delete(m); await db.commit(); return success_response(None,"Mapping deleted")

@router.get("/reports/users.csv")
async def users_csv(db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    rows=(await db.execute(select(User).options(selectinload(User.role_obj),selectinload(User.barangay)).order_by(User.id))).scalars().all(); f=io.StringIO(); w=csv.writer(f); w.writerow(["id","full_name","email","role","barangay","status"])
    for u in rows: w.writerow([u.id,u.full_name,u.email,u.role_obj.slug if u.role_obj else u.role,u.barangay.name if u.barangay else "",u.status])
    f.seek(0); return StreamingResponse(iter([f.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=users.csv"})

@router.get("/reports/completion.csv")
async def completion_csv(db:AsyncSession=Depends(get_db),_:User=Depends(require_admin)):
    f=io.StringIO(); w=csv.writer(f); w.writerow(["user_id","lesson_id","is_completed","completed_at"])
    for p in (await db.execute(select(LessonProgress))).scalars().all(): w.writerow([p.user_id,p.lesson_id,p.is_completed,p.completed_at])
    f.seek(0); return StreamingResponse(iter([f.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=completion.csv"})
