import os, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import TrainingMaterial, Lesson, Resource, User
from app.deps import get_current_user, require_admin
from app.response import success_response
from app.serializers import lesson_payload, resource_payload
from app.config import UPLOAD_DIR, MAX_UPLOAD_MB

router = APIRouter(prefix="/api", tags=["Materials"])
ALLOWED = {"pdf","zip","docx","pptx","mp4"}

@router.get("/materials/{material_id}/lessons")
async def lessons(material_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    rows=(await db.execute(select(Lesson).where(Lesson.material_id==material_id).order_by(Lesson.order_index, Lesson.lesson_number))).scalars().all()
    return success_response([await lesson_payload(db,l,user.id) for l in rows])

@router.get("/training-materials/{material_id}/uploads", tags=["Training Materials Uploads"] )
@router.get("/materials/{material_id}/resources")
async def resources(material_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    rows=(await db.execute(select(Resource).options(selectinload(Resource.uploaded_by)).where(Resource.material_id==material_id))).scalars().all()
    return success_response([resource_payload(r) for r in rows])

@router.post("/training-materials/{material_id}/uploads", tags=["Training Materials Uploads"] )
@router.post("/admin/materials/{material_id}/resources")
async def upload_resource(material_id:int, file:UploadFile=File(...), db:AsyncSession=Depends(get_db), user:User=Depends(require_admin)):
    if not await db.get(TrainingMaterial, material_id): raise HTTPException(404,"Material not found")
    ext=(file.filename or "").rsplit(".",1)[-1].lower()
    if ext not in ALLOWED: raise HTTPException(400,"Unsupported file type")
    content=await file.read()
    if len(content) > MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,"File too large")
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    stored=f"{uuid.uuid4().hex}.{ext}"; path=os.path.join(UPLOAD_DIR,stored)
    with open(path,"wb") as f: f.write(content)
    r=Resource(material_id=material_id,file_name=file.filename,stored_file_name=stored,file_type=ext,file_size=len(content),file_path=path,uploaded_by_id=user.id)
    db.add(r); await db.commit(); await db.refresh(r)
    return success_response(resource_payload(r),"Resource uploaded")

@router.get("/resources/{resource_id}/download")
async def download_resource(resource_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(get_current_user)):
    r=await db.get(Resource,resource_id)
    if not r: raise HTTPException(404,"Resource not found")
    if r.file_path and os.path.exists(r.file_path):
        return FileResponse(r.file_path, filename=r.file_name, media_type="application/octet-stream")
    return success_response({"file_name":r.file_name,"message":"No local file exists for seeded metadata"})

@router.delete("/admin/resources/{resource_id}")
async def delete_resource(resource_id:int, db:AsyncSession=Depends(get_db), user:User=Depends(require_admin)):
    r=await db.get(Resource,resource_id)
    if not r: raise HTTPException(404,"Resource not found")
    if r.file_path and os.path.exists(r.file_path): os.remove(r.file_path)
    await db.delete(r); await db.commit(); return success_response(None,"Resource deleted")
