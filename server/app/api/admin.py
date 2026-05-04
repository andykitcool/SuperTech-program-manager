from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.auth import get_current_user
from app.models import Activity, Program, ReadyMode, Video, Photo, SystemSettings, PrintRecord, Audience
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityOut, ProgramCreate, ProgramUpdate, ProgramOut, ProgramVideoOut
from app.schemas.program import ProgramBatchCreate

router = APIRouter()


def _match_photos_to_program(db: Session, program: Program):
    """根据节目的 start_time 和 duration，自动匹配同活动的照片并绑定。
    匹配规则：照片的 shoot_time 在 [start_time, start_time + duration] 范围内。
    如果 start_time 或 duration 发生变化，先释放旧绑定，再重新匹配。
    """
    from datetime import timedelta
    from app.models.photo import Photo
    from app.models.activity import ReadyStatus, VideoStatus

    if not program.start_time:
        # 没有录制时间，释放所有已绑定照片
        old_photos = db.query(Photo).filter(Photo.program_id == program.id).all()
        for photo in old_photos:
            photo.program_id = None
        program.photo_count = 0
        if program.ready_mode.value == "auto":
            program.ready_status = ReadyStatus.PENDING
        return

    # 先释放该节目已绑定的所有照片
    db.query(Photo).filter(Photo.program_id == program.id).update(
        {Photo.program_id: None}, synchronize_session="fetch"
    )
    db.flush()

    # 计算匹配时间范围
    start = program.start_time
    duration = program.duration or 0
    end = start + timedelta(seconds=duration) if duration > 0 else start

    # 查找同活动、时间范围内的、未被绑定到其他节目的照片
    matched_photos = db.query(Photo).filter(
        Photo.activity_id == program.activity_id,
        Photo.shoot_time >= start,
        Photo.shoot_time <= end,
        Photo.program_id.is_(None),
    ).all()

    for photo in matched_photos:
        photo.program_id = program.id
    db.flush()

    # 更新 photo_count
    program.photo_count = db.query(Photo).filter(
        Photo.program_id == program.id,
    ).count()

    # 自动就绪判断
    if program.ready_mode.value == "auto":
        if program.video_status == VideoStatus.READY and program.photo_count >= 1:
            program.ready_status = ReadyStatus.READY
        else:
            program.ready_status = ReadyStatus.PENDING


# ---- Activity CRUD ----

@router.get("/activities", response_model=List[ActivityOut])
def list_activities(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
    status: Optional[str] = None,
):
    query = db.query(Activity)
    if status:
        query = query.filter(Activity.status == status)
    activities = query.order_by(Activity.created_at.desc()).all()

    result = []
    for a in activities:
        out = ActivityOut.model_validate(a)
        out.program_count = len(a.programs)
        out.ready_program_count = sum(1 for p in a.programs if p.ready_status.value == "ready")
        result.append(out)
    return result


@router.post("/activities/cover/upload")
async def upload_activity_cover(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
):
    import os
    import shutil
    import uuid

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"

    upload_dir = os.path.join("uploads", "activity-covers")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(upload_dir, filename)

    with open(path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    return {
        "url": f"/uploads/activity-covers/{filename}",
        "filename": filename,
    }


@router.get("/activities/{activity_id}", response_model=ActivityOut)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    out = ActivityOut.model_validate(activity)
    out.program_count = len(activity.programs)
    out.ready_program_count = sum(1 for p in activity.programs if p.ready_status.value == "ready")
    return out


@router.post("/activities", response_model=ActivityOut)
def create_activity(
    data: ActivityCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    import uuid
    from datetime import date

    payload = data.model_dump()
    if not payload.get("storage_path_prefix"):
        payload["storage_path_prefix"] = f"activities/{date.today().strftime('%Y%m%d')}/{uuid.uuid4().hex[:8]}"
    if not payload.get("cover_image"):
        payload["cover_image"] = ""
    activity = Activity(**payload)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return ActivityOut.model_validate(activity)


@router.put("/activities/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: int,
    data: ActivityUpdate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(activity, key, value)
    db.commit()
    db.refresh(activity)
    out = ActivityOut.model_validate(activity)
    out.program_count = len(activity.programs)
    out.ready_program_count = sum(1 for p in activity.programs if p.ready_status.value == "ready")
    return out


@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.api.upload import _move_to_temp
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    # Move all video files to TEMP folder
    for program in activity.programs:
        if program.video_url:
            await _move_to_temp(program.video_url)
        for video in program.videos:
            if video.storage_url and video.storage_url != program.video_url:
                await _move_to_temp(video.storage_url)
    db.delete(activity)
    db.commit()
    return {"message": "deleted"}


# ---- Program CRUD ----

@router.get("/activities/{activity_id}/programs", response_model=List[ProgramOut])
def list_programs(
    activity_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.storage_service import get_video_thumbnail_url
    programs = (
        db.query(Program)
        .filter(Program.activity_id == activity_id)
        .order_by(Program.sequence_number)
        .all()
    )
    result = []
    for p in programs:
        out = ProgramOut.model_validate(p)
        out.video_thumbnail_url = get_video_thumbnail_url(p.video_url) if p.video_url else None
        out.videos = [
            ProgramVideoOut(
                id=video.id,
                filename=video.filename,
                file_size=video.file_size,
                duration=video.duration,
                recorded_at=video.recorded_at,
                storage_url=video.storage_url,
                storage_provider=video.storage_provider.value if hasattr(video.storage_provider, "value") else str(video.storage_provider),
                upload_type=video.upload_type.value if hasattr(video.upload_type, "value") else str(video.upload_type),
                upload_source=video.upload_source,
                status=video.status.value if hasattr(video.status, "value") else str(video.status),
                created_at=video.created_at,
                updated_at=video.updated_at,
            )
            for video in sorted(p.videos, key=lambda item: item.created_at, reverse=True)
        ]
        result.append(out)
    return result


@router.post("/activities/{activity_id}/programs", response_model=ProgramOut)
def create_program(
    activity_id: int,
    data: ProgramCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    program = Program(activity_id=activity_id, **data.model_dump())
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


@router.put("/programs/{program_id}", response_model=ProgramOut)
def update_program(
    program_id: int,
    data: ProgramUpdate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(program, key, value)

    # 如果 start_time 或 duration 被更新，触发照片匹配
    updated_fields = data.model_dump(exclude_unset=True)
    if "start_time" in updated_fields or "duration" in updated_fields:
        _match_photos_to_program(db, program)

    db.commit()
    db.refresh(program)
    return program


@router.delete("/programs/{program_id}")
async def delete_program(
    program_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.api.upload import _move_to_temp
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    # Move video files to TEMP folder
    if program.video_url:
        await _move_to_temp(program.video_url)
    for video in program.videos:
        if video.storage_url and video.storage_url != program.video_url:
            await _move_to_temp(video.storage_url)
    db.delete(program)
    db.commit()
    return {"message": "deleted"}


# ---- Program Batch Create ----

@router.post("/activities/{activity_id}/programs/batch", response_model=List[ProgramOut])
def batch_create_programs(
    activity_id: int,
    data: ProgramBatchCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    programs = []
    for item in data.programs:
        program = Program(activity_id=activity_id, **item.model_dump())
        db.add(program)
        programs.append(program)
    db.commit()
    for p in programs:
        db.refresh(p)
    return programs


# ---- Program Excel Import ----

@router.post("/activities/{activity_id}/programs/import", response_model=List[ProgramOut])
def import_programs_excel(
    activity_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """通过上传Excel表格批量导入节目"""
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式")

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    try:
        import openpyxl
        from io import BytesIO

        content = file.file.read()
        wb = openpyxl.load_workbook(BytesIO(content), read_only=True)
        ws = wb.active
        if not ws:
            raise HTTPException(status_code=400, detail="Excel文件为空")

        rows = list(ws.iter_rows(min_row=1, values_only=True))
        if len(rows) < 2:
            raise HTTPException(status_code=400, detail="Excel文件至少需要表头和一行数据")

        # 第一行为表头，解析列映射
        header = [str(c).strip().lower() if c else '' for c in rows[0]]
        col_map = {}
        for i, h in enumerate(header):
            if h in ('节目名称', '名称', 'name', '节目'):
                col_map['name'] = i
            elif h in ('节目号', '序号', '编号', 'sequence', 'order'):
                col_map['sequence_number'] = i
            elif h in ('开始时间', '录制开始', 'start_time', '开始'):
                col_map['start_time'] = i
            elif h in ('结束时间', '录制结束', 'end_time', '结束'):
                col_map['end_time'] = i
            elif h in ('就绪模式', 'ready_mode'):
                col_map['ready_mode'] = i

        if 'name' not in col_map:
            raise HTTPException(
                status_code=400,
                detail="未找到'节目名称'列，请确保表头包含：节目名称、节目号、开始时间、结束时间",
            )

        from datetime import datetime as dt
        programs = []
        for row in rows[1:]:
            if not row or col_map['name'] >= len(row) or not row[col_map['name']]:
                continue

            name = str(row[col_map['name']]).strip()
            seq = int(row[col_map.get('sequence_number', 1)]) if col_map.get('sequence_number') in col_map and col_map.get('sequence_number', 1) < len(row) and row[col_map.get('sequence_number', 1)] else len(programs) + 1

            start_time = None
            if 'start_time' in col_map and col_map['start_time'] < len(row) and row[col_map['start_time']]:
                try:
                    val = row[col_map['start_time']]
                    if isinstance(val, dt):
                        start_time = val
                    elif hasattr(val, 'isoformat'):
                        start_time = val.isoformat()
                    else:
                        from dateutil import parser as dp
                        start_time = dp.parse(str(val))
                except Exception:
                    pass

            end_time = None
            if 'end_time' in col_map and col_map['end_time'] < len(row) and row[col_map['end_time']]:
                try:
                    val = row[col_map['end_time']]
                    if isinstance(val, dt):
                        end_time = val
                    elif hasattr(val, 'isoformat'):
                        end_time = val.isoformat()
                    else:
                        from dateutil import parser as dp
                        end_time = dp.parse(str(val))
                except Exception:
                    pass

            ready_mode = ReadyMode.AUTO
            if 'ready_mode' in col_map and col_map['ready_mode'] < len(row) and row[col_map['ready_mode']]:
                mode_str = str(row[col_map['ready_mode']]).strip().lower()
                if mode_str in ('手动', 'manual'):
                    ready_mode = ReadyMode.MANUAL

            program = Program(
                activity_id=activity_id,
                name=name,
                sequence_number=seq,
                start_time=start_time,
                end_time=end_time,
                ready_mode=ready_mode,
            )
            db.add(program)
            programs.append(program)

        if not programs:
            raise HTTPException(status_code=400, detail="未解析到有效数据行")

        db.commit()
        for p in programs:
            db.refresh(p)
        return programs

    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=500, detail="服务端缺少 openpyxl 依赖，请执行 pip install openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel解析失败: {str(e)}")


# ---- Print Records ----

@router.get("/activities/{activity_id}/print-records")
def list_print_records(
    activity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    query = db.query(PrintRecord).filter(PrintRecord.activity_id == activity_id)
    total = query.count()
    records = (
        query.order_by(PrintRecord.created_at.desc(), PrintRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for record in records:
        program = db.query(Program).filter(Program.id == record.program_id).first() if record.program_id else None
        photo = db.query(Photo).filter(Photo.id == record.photo_id).first() if record.photo_id else None
        items.append({
            "id": record.id,
            "activity_id": record.activity_id,
            "program_id": record.program_id,
            "program_name": program.name if program else None,
            "program_sequence_number": program.sequence_number if program else None,
            "photo_id": record.photo_id,
            "photo_url": (photo.storage_url or photo.wotu_url) if photo else None,
            "photo_filename": photo.filename if photo else None,
            "user_identifier": record.user_identifier,
            "user_name": record.user_name,
            "template_name": record.template_name,
            "paper_size": record.paper_size,
            "copies": record.copies,
            "status": record.status,
            "task_id": record.task_id,
            "error_msg": record.error_msg,
            "printed_at": str(record.printed_at) if record.printed_at else None,
            "created_at": str(record.created_at) if record.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class CreatePrintRecordRequest(BaseModel):
    photo_id: int
    copies: int = Field(1, ge=1, le=99)
    user_identifier: Optional[str] = None
    user_name: Optional[str] = None


def _load_activity_print_template(db: Session, activity_id: int) -> dict:
    import json
    setting = db.query(SystemSettings).filter(
        SystemSettings.key == f"activity_{activity_id}_print_template"
    ).first()
    if not setting or not setting.value:
        return {}
    try:
        return json.loads(setting.value)
    except Exception:
        return {}


@router.post("/activities/{activity_id}/print-records")
def create_print_record(
    activity_id: int,
    data: CreatePrintRecordRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    photo = db.query(Photo).filter(
        Photo.id == data.photo_id,
        Photo.activity_id == activity_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    template = _load_activity_print_template(db, activity_id)
    record = PrintRecord(
        activity_id=activity_id,
        program_id=photo.program_id,
        photo_id=photo.id,
        user_identifier=data.user_identifier or "admin",
        user_name=data.user_name or "管理员",
        template_name=template.get("templateName") or "默认模版",
        paper_size=template.get("dmPaperSize") or template.get("paperKey") or None,
        copies=data.copies,
        status="queued",
        print_payload_json=template and __import__("json").dumps(template, ensure_ascii=False) or None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "print queued", "record_id": record.id}


@router.post("/print-records/{record_id}/reprint")
def reprint_record(
    record_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Print record not found")

    new_record = PrintRecord(
        activity_id=record.activity_id,
        program_id=record.program_id,
        photo_id=record.photo_id,
        source_record_id=record.id,
        user_identifier=record.user_identifier,
        user_name=record.user_name,
        template_name=record.template_name,
        paper_size=record.paper_size,
        copies=record.copies,
        status="queued",
        print_payload_json=record.print_payload_json,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return {
        "message": "reprint queued",
        "record_id": new_record.id,
        "source_record_id": record.id,
    }


# ---- Share Settings / Audience ----

@router.get("/activities/{activity_id}/audiences")
def list_activity_audiences(
    activity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from datetime import datetime, timedelta

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    online_after = datetime.now() - timedelta(minutes=5)
    query = db.query(Audience).filter(Audience.activity_id == activity_id)
    total = query.count()
    audiences = (
        query.order_by(Audience.last_seen_at.desc(), Audience.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [
            {
                "id": item.id,
                "activity_id": item.activity_id,
                "openid": item.openid,
                "unionid": item.unionid,
                "nickname": item.nickname,
                "avatar_url": item.avatar_url,
                "phone": item.phone,
                "province": item.province,
                "city": item.city,
                "country": item.country,
                "first_ip": item.first_ip,
                "last_ip": item.last_ip,
                "first_client": item.first_client,
                "last_client": item.last_client,
                "is_online": item.last_seen_at and item.last_seen_at >= online_after,
                "is_blacklisted": item.is_blacklisted,
                "first_seen_at": str(item.first_seen_at) if item.first_seen_at else None,
                "last_seen_at": str(item.last_seen_at) if item.last_seen_at else None,
            }
            for item in audiences
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class AudienceBlacklistRequest(BaseModel):
    blacklisted: bool = True


@router.post("/audiences/{audience_id}/blacklist")
def update_audience_blacklist(
    audience_id: int,
    data: AudienceBlacklistRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    audience = db.query(Audience).filter(Audience.id == audience_id).first()
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")
    audience.is_blacklisted = data.blacklisted
    db.commit()
    db.refresh(audience)
    return {"message": "updated", "id": audience.id, "is_blacklisted": audience.is_blacklisted}


# ---- Auth ----


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_SETTING_KEY = "admin_password_hash"
DEFAULT_ADMIN_PASSWORD = "admin123"


def _get_admin_password_hash(db: Session) -> Optional[str]:
    setting = db.query(SystemSettings).filter(SystemSettings.key == ADMIN_PASSWORD_SETTING_KEY).first()
    return setting.value if setting and setting.value else None


def _verify_admin_password(db: Session, password: str) -> bool:
    from app.utils.auth import verify_password

    password_hash = _get_admin_password_hash(db)
    if password_hash:
        return verify_password(password, password_hash)
    return password == DEFAULT_ADMIN_PASSWORD


def _save_admin_password(db: Session, password: str) -> None:
    from app.utils.auth import get_password_hash

    password_hash = get_password_hash(password)
    setting = db.query(SystemSettings).filter(SystemSettings.key == ADMIN_PASSWORD_SETTING_KEY).first()
    if not setting:
        setting = SystemSettings(
            key=ADMIN_PASSWORD_SETTING_KEY,
            value=password_hash,
            description="Admin password hash",
        )
        db.add(setting)
    else:
        setting.value = password_hash
    db.commit()


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    from app.utils.auth import create_access_token

    if data.username != ADMIN_USERNAME or not _verify_admin_password(db, data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": data.username})
    return LoginResponse(access_token=token, username=data.username)


@router.put("/password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("sub") != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Only admin can change password")
    if not _verify_admin_password(db, data.old_password):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

    _save_admin_password(db, data.new_password)
    return {"message": "password updated"}


def verify_pw(plain: str, hashed: str) -> bool:
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return ctx.verify(plain, hashed)
