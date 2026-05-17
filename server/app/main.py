from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import secrets

from app.config import get_settings
from app.models import Base
from app.database import engine, SessionLocal

settings = get_settings()

UNSAFE_JWT_SECRET_KEYS = {
    "",
    "your-super-secret-key-change-in-production",
    "change-this-to-a-secure-random-string",
}
UNSAFE_ADMIN_PASSWORDS = {"", "admin", "admin123", "password", "123456"}


def _prepare_runtime_settings() -> None:
    """Validate production secrets and keep local development usable."""
    if settings.JWT_SECRET_KEY in UNSAFE_JWT_SECRET_KEYS or len(settings.JWT_SECRET_KEY) < 32:
        if settings.is_production:
            raise RuntimeError("JWT_SECRET_KEY must be set to a strong secret in production")
        settings.JWT_SECRET_KEY = secrets.token_urlsafe(48)

    if settings.is_production and settings.ADMIN_INITIAL_PASSWORD in UNSAFE_ADMIN_PASSWORDS:
        raise RuntimeError("ADMIN_INITIAL_PASSWORD must be changed in production")


def _init_database() -> None:
    # Auto-create tables
    Base.metadata.create_all(bind=engine)

    # Backfill and lightweight compatibility migrations for existing MySQL databases.
    _ensure_system_settings_value_capacity()
    _backfill_access_tokens()
    _ensure_activity_time_columns()
    _ensure_video_recorded_at_column()
    _ensure_activity_ready_mode_column()
    _ensure_activity_sync_mode_column()

    # Ensure short video columns on programs table
    _ensure_short_video_columns()

    # Ensure print payment columns on print_records table
    _ensure_print_payment_columns()
    _ensure_print_image_columns()
    _ensure_print_client_columns()
    _ensure_photo_category_columns()
    _ensure_app_user_auth_columns()

    _seed_roles_and_users()


def _ensure_system_settings_value_capacity():
    """Expand setting values for print template canvas JSON."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("SHOW COLUMNS FROM system_settings LIKE 'value'"))
        row = result.fetchone()
        column_type = str(row[1]).lower() if row and len(row) > 1 else ""
        if row and column_type != "longtext":
            db.execute(text("ALTER TABLE system_settings MODIFY COLUMN value LONGTEXT NULL"))
            db.commit()
    finally:
        db.close()


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


def _ensure_activity_ready_mode_column():
    """Add ready_mode column to activities table for activity-level ready mode control."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("SHOW COLUMNS FROM activities LIKE 'ready_mode'"))
        if not result.fetchone():
            db.execute(text("ALTER TABLE activities ADD COLUMN ready_mode VARCHAR(10) NOT NULL DEFAULT 'AUTO'"))
            db.commit()
    finally:
        db.close()


def _ensure_activity_sync_mode_column():
    """Add sync_mode column to activities table for local/api sync mode control."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("SHOW COLUMNS FROM activities LIKE 'sync_mode'"))
        if not result.fetchone():
            db.execute(text("ALTER TABLE activities ADD COLUMN sync_mode VARCHAR(10) NOT NULL DEFAULT 'local'"))
            db.commit()
    finally:
        db.close()


def _ensure_short_video_columns():
    """Add short_video_url and short_video_status columns to programs table."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        for col, column_def in [
            ("short_video_url", "VARCHAR(1000) NULL"),
            ("short_video_status", "VARCHAR(20) NOT NULL DEFAULT 'none'"),
        ]:
            result = db.execute(text(f"SHOW COLUMNS FROM programs LIKE '{col}'"))
            if not result.fetchone():
                db.execute(text(f"ALTER TABLE programs ADD COLUMN {col} {column_def}"))
                db.commit()
    finally:
        db.close()


def _ensure_print_payment_columns():
    """Add payment columns to print_records table for paid printing."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        for col, col_type in [
            ("payment_status", "VARCHAR(20) NOT NULL DEFAULT 'free'"),
            ("payment_order_id", "VARCHAR(64) NULL"),
            ("payment_amount", "INT NULL"),
            ("paid_at", "DATETIME NULL"),
        ]:
            result = db.execute(text(f"SHOW COLUMNS FROM print_records LIKE '{col}'"))
            if not result.fetchone():
                db.execute(text(f"ALTER TABLE print_records ADD COLUMN {col} {col_type}"))
                db.commit()
    finally:
        db.close()


def _ensure_print_image_columns():
    """Add persisted sent-print image columns to print_records."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("SHOW COLUMNS FROM print_records LIKE 'print_image_url'"))
        if not result.fetchone():
            db.execute(text("ALTER TABLE print_records ADD COLUMN print_image_url VARCHAR(1000) NULL AFTER print_payload_json"))
            db.commit()
    finally:
        db.close()


def _ensure_print_client_columns():
    """Add local print client dispatch columns to print_records."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        for col, col_type in [
            ("claimed_by", "VARCHAR(100) NULL"),
            ("claimed_at", "DATETIME NULL"),
            ("print_attempts", "INT NOT NULL DEFAULT 0"),
            ("local_job_id", "VARCHAR(100) NULL"),
        ]:
            result = db.execute(text(f"SHOW COLUMNS FROM print_records LIKE '{col}'"))
            if not result.fetchone():
                db.execute(text(f"ALTER TABLE print_records ADD COLUMN {col} {col_type}"))
                db.commit()
    finally:
        db.close()


def _ensure_photo_category_columns():
    """Add Wotu category fields to photos for categorized album display."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        for col, col_type in [
            ("wotu_category_id", "VARCHAR(200) NULL"),
            ("wotu_category_name", "VARCHAR(200) NULL"),
        ]:
            result = db.execute(text(f"SHOW COLUMNS FROM photos LIKE '{col}'"))
            if not result.fetchone():
                db.execute(text(f"ALTER TABLE photos ADD COLUMN {col} {col_type}"))
                db.commit()
    finally:
        db.close()


def _ensure_app_user_auth_columns():
    """Add self-registration account fields to app_users for existing databases."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "app_users" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("app_users")}
    dialect = engine.dialect.name
    db = SessionLocal()
    try:
        def add_column(name: str, mysql_type: str, sqlite_type: str) -> None:
            if name in existing:
                return
            column_type = sqlite_type if dialect == "sqlite" else mysql_type
            db.execute(text(f"ALTER TABLE app_users ADD COLUMN {name} {column_type}"))
            existing.add(name)

        add_column("source", "VARCHAR(20) NOT NULL DEFAULT 'wechat'", "VARCHAR(20) NOT NULL DEFAULT 'wechat'")
        add_column("username", "VARCHAR(80) NULL", "VARCHAR(80) NULL")
        add_column("password_hash", "VARCHAR(255) NULL", "VARCHAR(255) NULL")
        db.execute(text("UPDATE app_users SET source = 'wechat' WHERE source IS NULL OR source = ''"))
        db.commit()
    finally:
        db.close()


def _seed_roles_and_users():
    """Create default roles and backfill app users from existing audience rows."""
    from app.models import Audience
    from app.models.user import AppUser
    from app.utils.rbac import seed_default_roles

    db = SessionLocal()
    try:
        seed_default_roles(db)
        audiences = db.query(Audience).all()
        for audience in audiences:
            if not audience.openid:
                continue
            user = db.query(AppUser).filter(AppUser.openid == audience.openid).first()
            if not user:
                user = AppUser(openid=audience.openid, source="wechat")
                db.add(user)
            user.source = user.source or "wechat"
            user.unionid = user.unionid or audience.unionid
            user.nickname = user.nickname or audience.nickname
            user.avatar_url = user.avatar_url or audience.avatar_url
            user.phone = user.phone or audience.phone
            user.province = user.province or audience.province
            user.city = user.city or audience.city
            user.country = user.country or audience.country
            user.last_seen_at = audience.last_seen_at
            user.is_blacklisted = bool(user.is_blacklisted or audience.is_blacklisted)
        db.commit()
    finally:
        db.close()


def create_app() -> FastAPI:
    _prepare_runtime_settings()

    app = FastAPI(
        title="SuperTech Program Manager",
        description="少儿舞蹈展演素材交付系统",
        version="1.0.0",
    )

    @app.on_event("startup")
    def startup_event():
        _init_database()
        from app.utils.print_dispatcher import start_print_polling_if_needed

        start_print_polling_if_needed()

    import os
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials="*" not in settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and mount routers
    from app.api import admin, public, upload, settings as settings_api, wotu, music, short_video
    from app.api import material, download, payment, image_process, print_client

    app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])
    app.include_router(public.router, prefix="/api/public", tags=["家长端"])
    app.include_router(upload.router, prefix="/api/upload", tags=["上传"])
    app.include_router(settings_api.router, prefix="/api/settings", tags=["系统设置"])
    app.include_router(wotu.router, prefix="/api/admin", tags=["喔图同步"])
    app.include_router(music.router, prefix="/api/admin", tags=["热门曲库"])
    app.include_router(short_video.router, prefix="/api/admin", tags=["短视频管理"])
    app.include_router(material.router, prefix="/api/admin/materials", tags=["装饰素材管理"])
    app.include_router(download.router, prefix="/api/public/download", tags=["下载记录"])
    app.include_router(payment.router, prefix="/api", tags=["打印支付"])
    app.include_router(image_process.router, prefix="/api/public/image", tags=["图片处理"])
    app.include_router(print_client.router, prefix="/api/print-client", tags=["本地打印客户端"])

    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
