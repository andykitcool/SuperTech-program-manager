from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import String, or_
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.auth import get_current_user
from app.models import Activity, Program, ReadyMode, Video, Photo, SystemSettings, PrintRecord, Audience, DecorationMaterial, AppUser, Role, UserRoleAssignment
from app.utils.rbac import (
    PERMISSIONS,
    allowed_activity_ids,
    can_manage_all_activities,
    is_super_admin,
    parse_permissions,
    permissions_to_json,
    require_activity_access,
    require_permission,
    user_permissions,
)
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityOut, ProgramCreate, ProgramUpdate, ProgramOut, ProgramVideoOut
from app.schemas.program import ProgramBatchCreate
from app.api.material import PrintSettingsUpdate
from app.utils.activity_print_settings import get_activity_print_settings, update_activity_print_settings

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
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = None,
):
    query = db.query(Activity)
    permissions = set(current_user.get("permissions") or [])
    ids = allowed_activity_ids(current_user)
    if ids is not None and "print.manage" not in permissions:
        if not ids:
            return []
        query = query.filter(Activity.id.in_(ids))
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
    from app.utils.cloud_assets import upload_image_to_cloud

    return await upload_image_to_cloud(
        file,
        prefix="activity-covers",
        allowed_extensions={".jpg", ".jpeg", ".png", ".webp"},
    )


@router.get("/activities/{activity_id}", response_model=ActivityOut)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    activity = require_activity_access(db, current_user, activity_id)
    out = ActivityOut.model_validate(activity)
    out.program_count = len(activity.programs)
    out.ready_program_count = sum(1 for p in activity.programs if p.ready_status.value == "ready")
    return out


@router.post("/activities", response_model=ActivityOut)
def create_activity(
    data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "activity.manage")
    if not can_manage_all_activities(current_user):
        raise HTTPException(status_code=403, detail="没有创建活动的权限")
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
    current_user: dict = Depends(get_current_user),
):
    from app.models.activity import ReadyMode as ActReadyMode, ReadyStatus
    activity = require_activity_access(db, current_user, activity_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(activity, key, value)

    # If ready_mode changed, cascade to all programs
    if "ready_mode" in update_data:
        new_mode = ActReadyMode(update_data["ready_mode"]) if isinstance(update_data["ready_mode"], str) else update_data["ready_mode"]
        programs = db.query(Program).filter(Program.activity_id == activity_id).all()
        for program in programs:
            program.ready_mode = new_mode
            if new_mode == ActReadyMode.AUTO:
                # Re-evaluate auto ready status
                if program.video_status.value == "ready" and program.photo_count >= 1:
                    program.ready_status = ReadyStatus.READY
                else:
                    program.ready_status = ReadyStatus.PENDING

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
    current_user: dict = Depends(get_current_user),
):
    from app.api.upload import _move_to_temp
    if not can_manage_all_activities(current_user):
        raise HTTPException(status_code=403, detail="没有删除活动的权限")
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
    current_user: dict = Depends(get_current_user),
):
    from app.services.storage_service import get_video_thumbnail_url
    require_activity_access(db, current_user, activity_id, "program.manage")
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
    current_user: dict = Depends(get_current_user),
):
    activity = require_activity_access(db, current_user, activity_id, "program.manage")
    program_data = data.model_dump()
    # Inherit activity's ready_mode if not explicitly set
    if "ready_mode" not in program_data or program_data["ready_mode"] is None:
        program_data["ready_mode"] = activity.ready_mode
    program = Program(activity_id=activity_id, **program_data)
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


@router.put("/programs/{program_id}", response_model=ProgramOut)
def update_program(
    program_id: int,
    data: ProgramUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    require_activity_access(db, current_user, program.activity_id, "program.manage")
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
    current_user: dict = Depends(get_current_user),
):
    from app.api.upload import _move_to_temp
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    require_activity_access(db, current_user, program.activity_id, "program.manage")
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
    current_user: dict = Depends(get_current_user),
):
    activity = require_activity_access(db, current_user, activity_id, "program.manage")
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
    current_user: dict = Depends(get_current_user),
):
    """通过上传Excel表格批量导入节目"""
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式")

    activity = require_activity_access(db, current_user, activity_id, "program.manage")

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

            ready_mode = activity.ready_mode

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


def _print_record_photo_url(photo: Optional[Photo]) -> Optional[str]:
    return (photo.storage_url or photo.wotu_url) if photo else None


def _serialize_print_record(db: Session, record: PrintRecord, *, include_activity: bool = False) -> dict:
    program = db.query(Program).filter(Program.id == record.program_id).first() if record.program_id else None
    photo = db.query(Photo).filter(Photo.id == record.photo_id).first() if record.photo_id else None
    activity = db.query(Activity).filter(Activity.id == record.activity_id).first() if include_activity else None

    app_user = None
    audience = None
    if record.user_identifier:
        app_user = db.query(AppUser).filter(AppUser.openid == record.user_identifier).first()
        audience = db.query(Audience).filter(
            Audience.activity_id == record.activity_id,
            Audience.openid == record.user_identifier,
        ).first()

    nickname = (
        (app_user.nickname if app_user else None)
        or (audience.nickname if audience else None)
        or record.user_name
    )
    avatar_url = (
        (app_user.avatar_url if app_user else None)
        or (audience.avatar_url if audience else None)
    )
    order_no = record.payment_order_id or f"P{record.id:08d}"
    original_photo_url = _print_record_photo_url(photo)
    display_photo_url = record.print_image_url or original_photo_url

    item = {
        "id": record.id,
        "order_no": order_no,
        "activity_id": record.activity_id,
        "program_id": record.program_id,
        "program_name": program.name if program else None,
        "program_sequence_number": program.sequence_number if program else None,
        "photo_id": record.photo_id,
        "photo_url": display_photo_url,
        "original_photo_url": original_photo_url,
        "print_image_url": record.print_image_url,
        "photo_filename": photo.filename if photo else None,
        "user_identifier": record.user_identifier,
        "user_name": record.user_name,
        "nickname": nickname,
        "avatar_url": avatar_url,
        "template_name": record.template_name,
        "paper_size": record.paper_size,
        "copies": record.copies,
        "status": record.status,
        "task_id": record.task_id,
        "error_msg": record.error_msg,
        "payment_status": record.payment_status,
        "payment_order_id": record.payment_order_id,
        "payment_amount": record.payment_amount,
        "paid_at": str(record.paid_at) if record.paid_at else None,
        "printed_at": str(record.printed_at) if record.printed_at else None,
        "created_at": str(record.created_at) if record.created_at else None,
    }
    if include_activity:
        item["activity_name"] = activity.name if activity else None
    return item


@router.get("/activities/{activity_id}/print-records")
def list_print_records(
    activity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    permissions = set(current_user.get("permissions") or [])
    if not is_super_admin(current_user) and "print.manage" in permissions:
        activity = db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="活动不存在")
    else:
        require_activity_access(db, current_user, activity_id, "activity.manage")

    query = db.query(PrintRecord).filter(PrintRecord.activity_id == activity_id)
    total = query.count()
    records = (
        query.order_by(PrintRecord.created_at.desc(), PrintRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_serialize_print_record(db, record) for record in records]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/print-records")
def list_all_print_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    activity_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, max_length=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "print.manage")

    query = db.query(PrintRecord)
    allowed_ids = allowed_activity_ids(current_user)
    if allowed_ids is not None:
        if not allowed_ids:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        query = query.filter(PrintRecord.activity_id.in_(allowed_ids))
    if activity_id:
        query = query.filter(PrintRecord.activity_id == activity_id)
    if status:
        query = query.filter(PrintRecord.status == status)
    if keyword:
        text = f"%{keyword.strip()}%"
        program_ids = [
            item.id for item in db.query(Program.id).filter(
                or_(
                    Program.name.like(text),
                    Program.sequence_number.cast(String).like(text),
                )
            ).all()
        ]
        filters = [
            PrintRecord.user_name.like(text),
            PrintRecord.user_identifier.like(text),
            PrintRecord.payment_order_id.like(text),
            PrintRecord.task_id.like(text),
        ]
        if keyword.strip().isdigit():
            filters.append(PrintRecord.id == int(keyword.strip()))
        if program_ids:
            filters.append(PrintRecord.program_id.in_(program_ids))
        query = query.filter(or_(*filters))

    total = query.count()
    records = (
        query.order_by(PrintRecord.created_at.desc(), PrintRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_serialize_print_record(db, record, include_activity=True) for record in records],
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


def _template_uses_activity_paper(template: dict) -> bool:
    if template.get("printConfigMode") == "activity":
        return True
    if template.get("activeTemplateId") or template.get("templates"):
        return True
    return bool(template.get("paperWidthMm") and template.get("paperHeightMm"))


def _activity_template_paper_size(template: dict) -> Optional[str]:
    if not _template_uses_activity_paper(template):
        return None
    value = str(template.get("dmPaperSize") or "").strip()
    if value.isdigit():
        return value
    if template.get("paperWidthMm") and template.get("paperHeightMm"):
        return "0"
    return None


@router.post("/activities/{activity_id}/print-records")
def create_print_record(
    activity_id: int,
    data: CreatePrintRecordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_activity_access(db, current_user, activity_id, "activity.manage")

    photo = db.query(Photo).filter(
        Photo.id == data.photo_id,
        Photo.activity_id == activity_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    template = _load_activity_print_template(db, activity_id)
    import json

    # 检查蓝阔云打印是否启用
    from app.utils.lankuo_client import get_effective_lankuo_config
    from app.utils.print_dispatcher import should_dispatch_lankuo
    lankuo_cfg = get_effective_lankuo_config(db, activity_id)
    dispatch_lankuo = should_dispatch_lankuo(db, lankuo_cfg, activity_id)
    initial_status = "printing" if dispatch_lankuo else "queued"

    record = PrintRecord(
        activity_id=activity_id,
        program_id=photo.program_id,
        photo_id=photo.id,
        user_identifier=data.user_identifier or "admin",
        user_name=data.user_name or "管理员",
        template_name=template.get("templateName") or "默认模版",
        paper_size=_activity_template_paper_size(template),
        copies=data.copies,
        status=initial_status,
        print_payload_json=json.dumps(template, ensure_ascii=False) if template else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # 如果蓝阔云打印已启用，异步提交打印任务
    if dispatch_lankuo:
        from app.utils.print_dispatcher import dispatch_print_task
        dispatch_print_task(record.id, lankuo_cfg, db)

    return {"message": "print queued", "record_id": record.id}


@router.get("/activities/{activity_id}/print-settings")
def get_activity_print_settings_api(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_activity_access(db, current_user, activity_id, "print.manage")
    return get_activity_print_settings(db, activity_id)


@router.put("/activities/{activity_id}/print-settings")
def update_activity_print_settings_api(
    activity_id: int,
    data: PrintSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_activity_access(db, current_user, activity_id, "print.manage")
    return update_activity_print_settings(db, activity_id, data.model_dump(exclude_unset=True))


@router.post("/print-records/{record_id}/reprint")
def reprint_record(
    record_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Print record not found")

    from app.utils.lankuo_client import get_effective_lankuo_config
    from app.utils.print_dispatcher import should_dispatch_lankuo
    lankuo_cfg = get_effective_lankuo_config(db, record.activity_id)
    dispatch_lankuo = should_dispatch_lankuo(db, lankuo_cfg, record.activity_id)

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
        status="printing" if dispatch_lankuo else "queued",
        print_payload_json=record.print_payload_json,
        print_image_url=record.print_image_url,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    # 如果蓝阔云打印已启用，异步提交打印任务
    if dispatch_lankuo:
        from app.utils.print_dispatcher import dispatch_print_task
        dispatch_print_task(new_record.id, lankuo_cfg, db)

    return {
        "message": "reprint queued",
        "record_id": new_record.id,
        "source_record_id": record.id,
    }


@router.delete("/print-records/{record_id}")
def delete_print_record(
    record_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Print record not found")
    if record.status not in ("failed", "queued"):
        raise HTTPException(status_code=400, detail="Only failed or queued print records can be deleted")

    db.delete(record)
    db.commit()
    return {"message": "deleted", "id": record_id}


# ---- Share Settings / Audience ----

@router.get("/activities/{activity_id}/audiences")
def list_activity_audiences(
    activity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from datetime import datetime, timedelta

    require_activity_access(db, current_user, activity_id, "activity.manage")

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


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")
    password: str = Field(..., min_length=6, max_length=72)
    nickname: Optional[str] = Field(None, max_length=100)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=72)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role_codes: List[str] = []
    permissions: List[str] = []
    activity_ids: List[int] = []


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_SETTING_KEY = "admin_password_hash"


def _get_admin_password_hash(db: Session) -> Optional[str]:
    setting = db.query(SystemSettings).filter(SystemSettings.key == ADMIN_PASSWORD_SETTING_KEY).first()
    return setting.value if setting and setting.value else None


def _verify_admin_password(db: Session, password: str) -> bool:
    from app.config import get_settings
    from app.utils.auth import verify_password

    password_hash = _get_admin_password_hash(db)
    if password_hash:
        return verify_password(password, password_hash)
    initial_password = get_settings().ADMIN_INITIAL_PASSWORD
    return bool(initial_password) and password == initial_password


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
    from app.utils.auth import create_access_token, verify_password

    username = data.username.strip()
    if username == ADMIN_USERNAME:
        if not _verify_admin_password(db, data.password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        permissions = list(PERMISSIONS.keys())
        token = create_access_token({
            "sub": username,
            "role_codes": ["super_admin"],
            "permissions": permissions,
            "activity_ids": [],
            "source": "system",
        })
        return LoginResponse(
            access_token=token,
            username=username,
            role_codes=["super_admin"],
            permissions=permissions,
            activity_ids=[],
        )

    user = (
        db.query(AppUser)
        .filter(AppUser.source == "self", AppUser.username == username, AppUser.is_deleted.is_(False))
        .first()
    )
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.is_blacklisted:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    permissions, activity_ids, role_codes = user_permissions(db, user.openid)
    token = create_access_token({
        "sub": username,
        "user_id": user.id,
        "openid": user.openid,
        "role_codes": role_codes,
        "permissions": sorted(permissions),
        "activity_ids": sorted(activity_ids),
        "source": "self",
    })
    return LoginResponse(
        access_token=token,
        username=username,
        role_codes=role_codes,
        permissions=sorted(permissions),
        activity_ids=sorted(activity_ids),
    )


@router.post("/register", response_model=LoginResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    from app.utils.auth import create_access_token, get_password_hash

    username = data.username.strip()
    if username.lower() == ADMIN_USERNAME:
        raise HTTPException(status_code=400, detail="该用户名不可注册")
    if db.query(AppUser).filter(AppUser.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = AppUser(
        openid=f"local:{username}",
        source="self",
        username=username,
        nickname=data.nickname.strip() if data.nickname else username,
        password_hash=get_password_hash(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({
        "sub": username,
        "user_id": user.id,
        "openid": user.openid,
        "role_codes": [],
        "permissions": [],
        "activity_ids": [],
        "source": "self",
    })
    return LoginResponse(access_token=token, username=username, role_codes=[], permissions=[], activity_ids=[])


@router.put("/password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

    if current_user.get("sub") == ADMIN_USERNAME:
        if not _verify_admin_password(db, data.old_password):
            raise HTTPException(status_code=400, detail="原密码不正确")
        _save_admin_password(db, data.new_password)
        return {"message": "password updated"}

    from app.utils.auth import get_password_hash, verify_password

    user_id = current_user.get("user_id")
    user = db.query(AppUser).filter(AppUser.id == user_id, AppUser.source == "self", AppUser.is_deleted.is_(False)).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=403, detail="当前账号不支持修改密码")
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"message": "password updated"}

def verify_pw(plain: str, hashed: str) -> bool:
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return ctx.verify(plain, hashed)


class RolePayload(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    permissions: List[str] = []


class UserRoleAssignmentPayload(BaseModel):
    role_id: int
    activity_ids: List[int] = []


class UserRolesUpdate(BaseModel):
    assignments: List[UserRoleAssignmentPayload] = []


class UserBlacklistRequest(BaseModel):
    blacklisted: bool


def _role_out(role: Role) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "description": role.description,
        "permissions": parse_permissions(role.permissions_json),
        "is_system": role.is_system,
        "created_at": str(role.created_at) if role.created_at else None,
    }


def _user_out(db: Session, user: AppUser) -> dict:
    assignments = []
    for assignment in user.assignments:
        if not assignment.role:
            continue
        activity = db.query(Activity).filter(Activity.id == assignment.activity_id).first() if assignment.activity_id else None
        assignments.append({
            "id": assignment.id,
            "role_id": assignment.role_id,
            "role_name": assignment.role.name,
            "role_code": assignment.role.code,
            "permissions": parse_permissions(assignment.role.permissions_json),
            "activity_id": assignment.activity_id,
            "activity_name": activity.name if activity else None,
        })
    permissions, activity_ids, role_codes = user_permissions(db, user.openid)
    return {
        "id": user.id,
        "openid": user.openid,
        "source": user.source,
        "username": user.username,
        "unionid": user.unionid,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "phone": user.phone,
        "province": user.province,
        "city": user.city,
        "country": user.country,
        "is_blacklisted": user.is_blacklisted,
        "is_deleted": user.is_deleted,
        "last_seen_at": str(user.last_seen_at) if user.last_seen_at else None,
        "created_at": str(user.created_at) if user.created_at else None,
        "role_codes": role_codes,
        "permissions": sorted(permissions),
        "activity_ids": sorted(activity_ids),
        "assignments": assignments,
    }


@router.get("/permissions")
def list_permissions(current_user: dict = Depends(get_current_user)):
    require_permission(current_user, "role.manage")
    return [{"key": key, "label": label} for key, label in PERMISSIONS.items()]


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "role.manage")
    roles = db.query(Role).order_by(Role.is_system.desc(), Role.id.asc()).all()
    return [_role_out(role) for role in roles]


@router.post("/roles")
def create_role(
    data: RolePayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "role.manage")
    if db.query(Role).filter((Role.code == data.code) | (Role.name == data.name)).first():
        raise HTTPException(status_code=400, detail="角色名称或编码已存在")
    invalid = [item for item in data.permissions if item not in PERMISSIONS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"未知权限: {', '.join(invalid)}")
    role = Role(
        name=data.name,
        code=data.code,
        description=data.description,
        permissions_json=permissions_to_json(data.permissions),
        is_system=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return _role_out(role)


@router.put("/roles/{role_id}")
def update_role(
    role_id: int,
    data: RolePayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "role.manage")
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        role.description = data.description
        role.permissions_json = permissions_to_json(data.permissions)
    else:
        duplicate = db.query(Role).filter(Role.id != role_id, ((Role.code == data.code) | (Role.name == data.name))).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="角色名称或编码已存在")
        role.name = data.name
        role.code = data.code
        role.description = data.description
        role.permissions_json = permissions_to_json(data.permissions)
    db.commit()
    db.refresh(role)
    return _role_out(role)


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "role.manage")
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统默认角色不能删除")
    if role.assignments:
        raise HTTPException(status_code=400, detail="该角色仍有用户使用，不能删除")
    db.delete(role)
    db.commit()
    return {"message": "deleted", "id": role_id}


@router.get("/users")
def list_users(
    keyword: Optional[str] = Query(None),
    source: Optional[str] = Query(None, pattern="^(self|wechat)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "user.manage")
    query = db.query(AppUser).filter(AppUser.is_deleted.is_(False))
    if source == "self":
        query = query.filter(AppUser.source == "self")
    elif source == "wechat":
        query = query.filter(AppUser.source != "self")
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(AppUser.nickname.like(like), AppUser.username.like(like), AppUser.openid.like(like), AppUser.phone.like(like)))
    total = query.count()
    users = (
        query.order_by(AppUser.last_seen_at.desc(), AppUser.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_user_out(db, user) for user in users], "total": total, "page": page, "page_size": page_size}


@router.put("/users/{user_id}/blacklist")
def update_user_blacklist(
    user_id: int,
    data: UserBlacklistRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "user.manage")
    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_blacklisted = data.blacklisted
    db.query(Audience).filter(Audience.openid == user.openid).update({"is_blacklisted": data.blacklisted})
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "user.manage")
    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_deleted = True
    user.assignments.clear()
    db.commit()
    return {"message": "deleted", "id": user_id}


@router.put("/users/{user_id}/roles")
def update_user_roles(
    user_id: int,
    data: UserRolesUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "user.manage")
    user = db.query(AppUser).filter(AppUser.id == user_id, AppUser.is_deleted.is_(False)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.assignments.clear()
    db.flush()
    for assignment in data.assignments:
        role = db.query(Role).filter(Role.id == assignment.role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        permissions = parse_permissions(role.permissions_json)
        if role.code != "print_admin" and "activity.manage" in permissions and assignment.activity_ids:
            for activity_id in assignment.activity_ids:
                if not db.query(Activity).filter(Activity.id == activity_id).first():
                    raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
                db.add(UserRoleAssignment(user_id=user.id, role_id=role.id, activity_id=activity_id))
        else:
            db.add(UserRoleAssignment(user_id=user.id, role_id=role.id, activity_id=None))
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


# ============================================================
# Decoration Material CRUD
# ============================================================

class DecorationMaterialCreate(BaseModel):
    type: str = Field(..., description="background / frame / sticker")
    name: str
    storage_url: str
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class DecorationMaterialUpdate(BaseModel):
    name: Optional[str] = None
    storage_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/decoration-materials")
def list_decoration_materials(
    type: Optional[str] = Query(None, description="素材类型"),
    category: Optional[str] = Query(None, description="素材分类"),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "material.manage")
    """获取装饰素材列表"""
    query = db.query(DecorationMaterial)
    if type:
        query = query.filter(DecorationMaterial.type == type)
    if category:
        if type == "sticker" and category == "贴纸":
            query = query.filter(or_(
                DecorationMaterial.category == category,
                DecorationMaterial.category.is_(None),
                DecorationMaterial.category == "",
            ))
        else:
            query = query.filter(DecorationMaterial.category == category)
    if is_active is not None:
        query = query.filter(DecorationMaterial.is_active == is_active)
    total = query.count()
    items = (
        query.order_by(DecorationMaterial.sort_order.asc(), DecorationMaterial.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "type": item.type,
                "name": item.name,
                "storage_url": item.storage_url,
                "thumbnail_url": item.thumbnail_url,
                "category": item.category,
                "sort_order": item.sort_order,
                "is_active": item.is_active,
                "created_at": str(item.created_at) if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/decoration-materials", response_model=dict)
def create_decoration_material(
    data: DecorationMaterialCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "material.manage")
    """创建装饰素材"""
    if data.type not in ("background", "frame", "sticker"):
        raise HTTPException(status_code=400, detail="type must be background / frame / sticker")
    material = DecorationMaterial(**data.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return {"id": material.id, "message": "created"}


@router.put("/decoration-materials/{material_id}", response_model=dict)
def update_decoration_material(
    material_id: int,
    data: DecorationMaterialUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "material.manage")
    """更新装饰素材"""
    material = db.query(DecorationMaterial).filter(DecorationMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(material, key, value)
    db.commit()
    return {"id": material.id, "message": "updated"}


@router.delete("/decoration-materials/{material_id}")
def delete_decoration_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "material.manage")
    """删除装饰素材"""
    material = db.query(DecorationMaterial).filter(DecorationMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    db.delete(material)
    db.commit()
    return {"message": "deleted"}


# ============================================================
# Print Settings
# ============================================================

@router.get("/print-settings")
def get_print_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "print.manage")
    """获取打印设置"""
    from app.api.material import get_print_settings as _get_print_settings
    return _get_print_settings(db, current_user)


@router.put("/print-settings")
def update_print_settings(
    data: PrintSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "print.manage")
    """更新打印设置"""
    from app.api.material import update_print_settings as _update_print_settings
    return _update_print_settings(data, db, current_user)
