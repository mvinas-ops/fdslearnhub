from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.database import engine, Base, AsyncSessionLocal
from app.config import SEED_ON_STARTUP
from app.response import error_response, success_response
from app.seed import seed_database
from app.api.auth.routes import router as auth_router
from app.api.admin.routes import router as admin_router
from app.api.cml.routes import router as cml_router
from app.api.trainee.routes import router as trainee_router
from app.api.materials.routes import router as materials_router
from app.api.sessions.routes import router as sessions_router
from app.api.groups.routes import router as groups_router
from app.api.v1_aliases.routes import router as v1_alias_router

app = FastAPI(
    title="LearnHub API",
    version="1.1.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},  # hide bottom Schemas panel in /docs
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=error_response("Validation error", "VALIDATION_ERROR", exc.errors()))

@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=500, content=error_response("Database error occurred", "DB_ERROR", {"type": exc.__class__.__name__}))

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Keep HTTPException handling native; FastAPI catches it before this handler.
    return JSONResponse(status_code=500, content=error_response("Internal server error", "INTERNAL_ERROR", {"type": exc.__class__.__name__}))

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if SEED_ON_STARTUP:
        async with AsyncSessionLocal() as db:
            await seed_database(db)

@app.get("/api/health")
async def health():
    return success_response({"status": "ok"})

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(cml_router)
app.include_router(trainee_router)
app.include_router(materials_router)
app.include_router(sessions_router)
app.include_router(groups_router)
app.include_router(v1_alias_router)
