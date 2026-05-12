import json
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, Photo, PrintRecord, Program, SystemSettings
from app.utils.auth import get_current_user
from app.utils.rbac import require_permission

router = APIRouter()

PRINT_CLIENT_TOKEN_KEY = "print_client_token"
PRINT_CLIENT_SESSION_KEY_PREFIX = "print_client_session_"
WECHAT_PAY_ENABLED_KEY = "wechat_pay_enabled"
ALLOWED_CLIENT_STATUSES = {"claimed", "rendering", "printing", "success", "failed"}

class ClientSessionRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=100)
    client_name: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=50)


class HeartbeatRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=100)
    activity_id: Optional[int] = Field(None, ge=1)
    activity_name: Optional[str] = Field(None, max_length=200)
    version: Optional[str] = None
    printer_name: Optional[str] = None
    queue_length: int = 0
    status: str = "online"
    message: Optional[str] = None


class ClaimRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=100)
    activity_id: int = Field(..., ge=1)


class StatusRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=100)
    status: str
    message: Optional[str] = Field(None, max_length=500)
    local_job_id: Optional[str] = Field(None, max_length=100)
    print_image_url: Optional[str] = Field(None, max_length=1000)


def _session_key(client_id: str) -> str:
    return f"{PRINT_CLIENT_SESSION_KEY_PREFIX}{client_id}"


def _load_json_setting(setting: Optional[SystemSettings]) -> dict:
    if not setting or not setting.value:
        return {}
    try:
        value = json.loads(setting.value)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _find_client_session_by_token(db: Session, token: str) -> Optional[dict]:
    if not token:
        return None
    rows = (
        db.query(SystemSettings)
        .filter(SystemSettings.key.like(f"{PRINT_CLIENT_SESSION_KEY_PREFIX}%"))
        .all()
    )
    for row in rows:
        data = _load_json_setting(row)
        if data.get("client_token") == token and data.get("enabled", True):
            return data
    return None


def _expected_client_token(db: Session) -> Optional[str]:
    setting = db.query(SystemSettings).filter(SystemSettings.key == PRINT_CLIENT_TOKEN_KEY).first()
    value = setting.value if setting and setting.value else os.getenv("PRINT_CLIENT_TOKEN")
    return value.strip() if value else None


def _require_client_token(db: Session, x_print_client_token: Optional[str]) -> None:
    expected = _expected_client_token(db)
    if x_print_client_token and expected and x_print_client_token == expected:
        return
    if x_print_client_token and _find_client_session_by_token(db, x_print_client_token):
        return
    if not expected:
        raise HTTPException(status_code=503, detail="Print client credential is not configured")
    if not x_print_client_token:
        raise HTTPException(status_code=401, detail="Invalid print client token")
    raise HTTPException(status_code=401, detail="Invalid print client token")


def _load_payload(record: PrintRecord) -> dict:
    if not record.print_payload_json:
        return {}
    try:
        payload = json.loads(record.print_payload_json)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _payload_size(payload: dict) -> tuple[int, int]:
    width = payload.get("_canvas_width") or payload.get("width") or payload.get("canvasWidth") or 1800
    height = payload.get("_canvas_height") or payload.get("height") or payload.get("canvasHeight") or 1200
    try:
        width = int(float(width))
        height = int(float(height))
    except (TypeError, ValueError):
        width, height = 1800, 1200
    return max(1, min(width, 8000)), max(1, min(height, 8000))


def _payment_enabled(db: Session) -> bool:
    setting = db.query(SystemSettings).filter(SystemSettings.key == WECHAT_PAY_ENABLED_KEY).first()
    return bool(setting and str(setting.value or "").lower() == "true")


def _photo_url(photo: Optional[Photo]) -> Optional[str]:
    return (photo.storage_url or photo.wotu_url) if photo else None


def _serialize_job(db: Session, record: PrintRecord) -> dict:
    program = db.query(Program).filter(Program.id == record.program_id).first() if record.program_id else None
    activity = db.query(Activity).filter(Activity.id == record.activity_id).first()
    photo = db.query(Photo).filter(Photo.id == record.photo_id).first() if record.photo_id else None
    payload = _load_payload(record)
    width, height = _payload_size(payload)

    return {
        "id": str(record.id),
        "orderNo": record.payment_order_id or f"P{record.id:08d}",
        "programName": program.name if program else "",
        "activityName": activity.name if activity else "",
        "photoName": photo.filename if photo else "",
        "photoUrl": _photo_url(photo),
        "printImageUrl": record.print_image_url,
        "templateId": f"server-record-{record.id}",
        "templateName": record.template_name or "Server print payload",
        "paperName": record.paper_size or "",
        "widthPx": width,
        "heightPx": height,
        "dpi": 300,
        "smoothingMode": "auto",
        "copies": record.copies,
        "status": record.status,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
        "canvasJson": json.dumps(payload, ensure_ascii=False) if payload else "",
        "lastMessage": record.error_msg,
    }


@router.post("/session")
def create_client_session(
    data: ClientSessionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "print.manage")
    now = datetime.now()
    setting = db.query(SystemSettings).filter(SystemSettings.key == _session_key(data.client_id)).first()
    session = _load_json_setting(setting)
    client_token = session.get("client_token") or secrets.token_urlsafe(32)
    value = {
        "client_id": data.client_id,
        "client_name": data.client_name or session.get("client_name") or data.client_id,
        "client_token": client_token,
        "version": data.version,
        "issued_by": current_user.get("sub"),
        "issued_at": session.get("issued_at") or now.isoformat(),
        "last_seen_at": now.isoformat(),
        "enabled": True,
    }
    if not setting:
        setting = SystemSettings(
            key=_session_key(data.client_id),
            value=json.dumps(value, ensure_ascii=False),
            description="本地打印客户端设备凭证",
        )
        db.add(setting)
    else:
        setting.value = json.dumps(value, ensure_ascii=False)
        setting.description = setting.description or "本地打印客户端设备凭证"
    db.commit()
    return {
        "client_id": data.client_id,
        "client_token": client_token,
        "expires_at": None,
    }


@router.post("/heartbeat")
def heartbeat(
    data: HeartbeatRequest,
    db: Session = Depends(get_db),
    x_print_client_token: Optional[str] = Header(None),
):
    _require_client_token(db, x_print_client_token)
    setting = db.query(SystemSettings).filter(SystemSettings.key == f"print_client_heartbeat_{data.client_id}").first()
    value = {
        "client_id": data.client_id,
        "activity_id": data.activity_id,
        "activity_name": data.activity_name,
        "version": data.version,
        "printer_name": data.printer_name,
        "queue_length": data.queue_length,
        "status": data.status,
        "message": data.message,
        "last_seen_at": datetime.now().isoformat(),
    }
    if not setting:
        setting = SystemSettings(key=f"print_client_heartbeat_{data.client_id}", value=json.dumps(value, ensure_ascii=False))
        db.add(setting)
    else:
        setting.value = json.dumps(value, ensure_ascii=False)
    db.commit()
    return {"ok": True}


@router.post("/jobs/claim")
def claim_job(
    data: ClaimRequest,
    db: Session = Depends(get_db),
    x_print_client_token: Optional[str] = Header(None),
):
    _require_client_token(db, x_print_client_token)
    eligible_payment_statuses = ["free", "paid"]
    if not _payment_enabled(db):
        eligible_payment_statuses.append("pending")

    record = (
        db.query(PrintRecord)
        .filter(PrintRecord.status == "queued")
        .filter(PrintRecord.activity_id == data.activity_id)
        .filter(PrintRecord.payment_status.in_(eligible_payment_statuses))
        .order_by(PrintRecord.created_at.asc(), PrintRecord.id.asc())
        .first()
    )
    if not record:
        return {"job": None}

    if record.payment_status == "pending" and not _payment_enabled(db):
        record.payment_status = "free"
        record.payment_amount = 0
    record.status = "claimed"
    record.claimed_by = data.client_id
    record.claimed_at = datetime.now()
    record.print_attempts = (record.print_attempts or 0) + 1
    record.error_msg = None
    db.commit()
    db.refresh(record)
    return {"job": _serialize_job(db, record)}


@router.post("/jobs/{record_id}/status")
def update_job_status(
    record_id: int,
    data: StatusRequest,
    db: Session = Depends(get_db),
    x_print_client_token: Optional[str] = Header(None),
):
    _require_client_token(db, x_print_client_token)
    if data.status not in ALLOWED_CLIENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid print status")

    record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Print record not found")
    if record.claimed_by and record.claimed_by != data.client_id:
        raise HTTPException(status_code=409, detail="Print record claimed by another client")

    record.status = data.status
    record.claimed_by = record.claimed_by or data.client_id
    record.local_job_id = data.local_job_id or record.local_job_id
    if data.print_image_url:
        record.print_image_url = data.print_image_url
    if data.status == "success":
        record.printed_at = datetime.now()
        record.error_msg = None
    elif data.status == "failed":
        record.error_msg = data.message or "Local print failed"
    elif data.message:
        record.error_msg = data.message

    db.commit()
    return {"ok": True, "record_id": record.id, "status": record.status}
