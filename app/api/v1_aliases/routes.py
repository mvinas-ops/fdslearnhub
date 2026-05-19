from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/v1", tags=["v1 Compatibility"])

def keep_query(request: Request, path: str) -> str:
    qs = request.url.query
    return f"{path}?{qs}" if qs else path

@router.post("/auth/login", tags=["auth"])
async def v1_login(request: Request):
    return RedirectResponse(keep_query(request, "/api/auth/login"), status_code=307)

@router.post("/auth/refresh", tags=["auth"])
async def v1_refresh(request: Request):
    return RedirectResponse(keep_query(request, "/api/auth/refresh"), status_code=307)

@router.get("/me", tags=["auth"])
async def v1_me(request: Request):
    return RedirectResponse(keep_query(request, "/api/auth/me"), status_code=307)

@router.post("/auth/create-account", tags=["Create Account"])
@router.post("/auth/register", tags=["Create Account"])
async def v1_register(request: Request):
    return RedirectResponse(keep_query(request, "/api/auth/create-account"), status_code=307)

@router.get("/users", tags=["User Management"])
async def v1_users_list(request: Request):
    return RedirectResponse(keep_query(request, "/api/admin/users"), status_code=307)

@router.post("/users", tags=["User Management"])
async def v1_users_create(request: Request):
    return RedirectResponse(keep_query(request, "/api/admin/users"), status_code=307)

@router.put("/users/{user_id}", tags=["User Management"])
async def v1_users_update(user_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/admin/users/{user_id}"), status_code=307)

@router.delete("/users/{user_id}", tags=["User Management"])
async def v1_users_delete(user_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/admin/users/{user_id}"), status_code=307)

@router.get("/sessions", tags=["Sessions"])
async def v1_sessions_list(request: Request):
    return RedirectResponse(keep_query(request, "/api/sessions"), status_code=307)

@router.post("/sessions", tags=["Sessions"])
async def v1_sessions_create(request: Request):
    return RedirectResponse(keep_query(request, "/api/sessions"), status_code=307)

@router.get("/sessions/{session_id}", tags=["Sessions"])
async def v1_sessions_get(session_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/sessions/{session_id}"), status_code=307)

@router.put("/sessions/{session_id}", tags=["Sessions"])
async def v1_sessions_update(session_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/sessions/{session_id}"), status_code=307)

@router.patch("/sessions/{session_id}/attendance", tags=["Sessions"])
async def v1_sessions_attendance(session_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/sessions/{session_id}/attendance"), status_code=307)

@router.delete("/sessions/{session_id}", tags=["Sessions"])
async def v1_sessions_delete(session_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/sessions/{session_id}"), status_code=307)

@router.get("/client-groups", tags=["Client Groupings"])
async def v1_groups_list(request: Request):
    return RedirectResponse(keep_query(request, "/api/client-groups"), status_code=307)

@router.post("/client-groups", tags=["Client Groupings"])
async def v1_groups_create(request: Request):
    return RedirectResponse(keep_query(request, "/api/client-groups"), status_code=307)

@router.put("/client-groups/{group_id}", tags=["Client Groupings"])
async def v1_groups_update(group_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/client-groups/{group_id}"), status_code=307)

@router.delete("/client-groups/{group_id}", tags=["Client Groupings"])
async def v1_groups_delete(group_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/client-groups/{group_id}"), status_code=307)

@router.get("/training-materials", tags=["Training Materials"])
async def v1_materials_list(request: Request):
    return RedirectResponse(keep_query(request, "/api/admin/materials"), status_code=307)

@router.post("/training-materials", tags=["Training Materials"])
async def v1_materials_create(request: Request):
    return RedirectResponse(keep_query(request, "/api/admin/materials"), status_code=307)

@router.put("/training-materials/{material_id}", tags=["Training Materials"])
async def v1_materials_update(material_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/admin/materials/{material_id}"), status_code=307)

@router.delete("/training-materials/{material_id}", tags=["Training Materials"])
async def v1_materials_delete(material_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/admin/materials/{material_id}"), status_code=307)

@router.post("/training-materials/{material_id}/uploads", tags=["Training Materials Uploads"])
async def v1_upload_material_file(material_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/training-materials/{material_id}/uploads"), status_code=307)

@router.get("/training-materials/{material_id}/uploads", tags=["Training Materials Uploads"])
async def v1_list_material_files(material_id: int, request: Request):
    return RedirectResponse(keep_query(request, f"/api/training-materials/{material_id}/uploads"), status_code=307)
