from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import Base
from app.database import engine, SessionLocal

settings = get_settings()


def _backfill_access_tokens():
    """Backfill access_token for existing programs that don't have one."""
    from app.models.program import Program, _generate_access_token
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # Check if access_token column exists
        result = db.execute(text("SHOW COLUMNS FROM programs LIKE 'access_token'"))
        if not result.fetchone():
            db.execute(text("ALTER TABLE programs ADD COLUMN access_token VARCHAR(32) NOT NULL DEFAULT ''"))
            db.commit()

        # Backfill empty tokens
        programs = db.query(Program).filter(
            (Program.access_token == '') | (Program.access_token.is_(None))
        ).all()
        for p in programs:
            p.access_token = _generate_access_token()
        if programs:
            db.commit()
    finally:
        db.close()


def _ensure_activity_time_columns():
    """Add activity start/end datetime columns for existing MySQL databases."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        for column in ("start_time", "end_time"):
            result = db.execute(text(f"SHOW COLUMNS FROM activities LIKE '{column}'"))
            if not result.fetchone():
                db.execute(text(f"ALTER TABLE activities ADD COLUMN {column} DATETIME NULL"))
                db.commit()
    finally:
        db.close()


def _ensure_video_recorded_at_column():
    """Add per-video recorded_at column for repeated recordings."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("SHOW COLUMNS FROM videos LIKE 'recorded_at'"))
        if not result.fetchone():
            db.execute(text("ALTER TABLE videos ADD COLUMN recorded_at DATETIME NULL AFTER duration"))
            db.commit()
    finally:
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="SuperTech Program Manager",
        description="少儿舞蹈展演素材交付系统",
        version="1.0.0",
    )

    # Auto-create tables
    Base.metadata.create_all(bind=engine)

    # Backfill access_token for existing programs
    _backfill_access_tokens()
    _ensure_activity_time_columns()
    _ensure_video_recorded_at_column()

    import os
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and mount routers
    from app.api import admin, public, upload, settings as settings_api, wotu

    app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])
    app.include_router(public.router, prefix="/api/public", tags=["家长端"])
    app.include_router(upload.router, prefix="/api/upload", tags=["上传"])
    app.include_router(settings_api.router, prefix="/api/settings", tags=["系统设置"])
    app.include_router(wotu.router, prefix="/api/admin", tags=["喔图同步"])

    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
