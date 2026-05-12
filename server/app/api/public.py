from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Activity, ActivityStatus, AppUser, Audience, Program, Photo, PrintRecord, ReadyStatus, SystemSettings, DecorationMaterial
from app.schemas.photo import PhotoListOut
from app.schemas.activity import ProgramPublicOut
from app.utils.auth import create_access_token, decode_token
from app.utils.activity_print_settings import get_activity_print_settings
from app.utils.network_settings import build_public_url
from app.utils.rbac import user_permissions
from jose import JWTError

router = APIRouter()
security = HTTPBearer(auto_error=False)


class PublicPrintRequest(BaseModel):
    copies: int = Field(1, ge=1, le=99)
    user_identifier: Optional[str] = None
    user_name: Optional[str] = None


class WechatTrackRequest(BaseModel):
    activity_id: int
    openid: str
    unionid: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


def _check_admin_token(credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
    """Return True if a valid admin token is provided."""
    if not credentials:
        return False
    try:
        decode_token(credentials.credentials)
        return True
    except (JWTError, Exception):
        return False


def _get_program_by_token_or_404(token: str, db: Session, is_admin: bool) -> Program:
    program = db.query(Program).filter(Program.access_token == token).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    if not is_admin and program.ready_status.value != "ready":
        raise HTTPException(status_code=404, detail="Program not found or not ready")
    return program


def _load_json_setting(db: Session, key: str) -> dict:
    import json

    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting or not setting.value:
        return {}
    try:
        return json.loads(setting.value)
    except Exception:
        return {}


def _load_wechat_config(db: Session) -> dict:
    return _load_json_setting(db, "wechat_official_account_config")


def _client_label(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "micromessenger" in ua:
        return "微信手机版"
    if "mobile" in ua or "iphone" in ua or "android" in ua:
        return "手机浏览器"
    return "浏览器"


def _request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def _upsert_audience(db: Session, request: Request, profile: WechatTrackRequest) -> Audience:
    from datetime import datetime
    from app.utils.rbac import upsert_app_user_from_profile

    activity = db.query(Activity).filter(Activity.id == profile.activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    ip = _request_ip(request)
    user_agent = request.headers.get("user-agent", "")
    client = _client_label(user_agent)
    audience = db.query(Audience).filter(
        Audience.activity_id == profile.activity_id,
        Audience.openid == profile.openid,
    ).first()

    if not audience:
        audience = Audience(
            activity_id=profile.activity_id,
            openid=profile.openid,
            first_ip=ip,
            first_user_agent=user_agent[:500],
            first_client=client,
        )
        db.add(audience)

    audience.unionid = profile.unionid or audience.unionid
    audience.nickname = profile.nickname or audience.nickname
    audience.avatar_url = profile.avatar_url or audience.avatar_url
    audience.province = profile.province or audience.province
    audience.city = profile.city or audience.city
    audience.country = profile.country or audience.country
    audience.last_ip = ip
    audience.last_user_agent = user_agent[:500]
    audience.last_client = client
    audience.last_seen_at = datetime.now()
    audience.is_online = True
    app_user = upsert_app_user_from_profile(db, profile, audience.last_seen_at)
    if app_user.is_blacklisted:
        audience.is_blacklisted = True
    db.commit()
    db.refresh(audience)
    return audience


@router.get("/wechat/config")
def public_wechat_config(db: Session = Depends(get_db)):
    config = _load_wechat_config(db)
    return {
        "enabled": bool(config.get("enabled") and config.get("appid")),
        "appid": config.get("appid") or "",
        "scope": config.get("scope") or "snsapi_userinfo",
    }


@router.get("/wechat/oauth-url")
def public_wechat_oauth_url(
    redirect_uri: str,
    db: Session = Depends(get_db),
):
    from urllib.parse import quote

    config = _load_wechat_config(db)
    appid = config.get("appid")
    if not appid:
        raise HTTPException(status_code=400, detail="Wechat appid is not configured")
    scope = config.get("scope") or "snsapi_userinfo"
    state = config.get("state") or "supertech"
    url = (
        "https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={appid}"
        f"&redirect_uri={quote(redirect_uri, safe='')}"
        "&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
        "#wechat_redirect"
    )
    return {"url": url}


@router.get("/wechat/oauth-profile")
def public_wechat_oauth_profile(
    code: str,
    request: Request,
    activity_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    import httpx

    config = _load_wechat_config(db)
    appid = config.get("appid")
    appsecret = config.get("appsecret")
    if not appid or not appsecret:
        raise HTTPException(status_code=400, detail="Wechat appid/appsecret is not configured")

    token_url = "https://api.weixin.qq.com/sns/oauth2/access_token"
    userinfo_url = "https://api.weixin.qq.com/sns/userinfo"
    with httpx.Client(timeout=10) as client:
        token_res = client.get(token_url, params={
            "appid": appid,
            "secret": appsecret,
            "code": code,
            "grant_type": "authorization_code",
        }).json()
        if token_res.get("errcode"):
            raise HTTPException(status_code=400, detail=token_res.get("errmsg") or "Wechat oauth failed")

        userinfo_res = client.get(userinfo_url, params={
            "access_token": token_res.get("access_token"),
            "openid": token_res.get("openid"),
            "lang": "zh_CN",
        }).json()
        if userinfo_res.get("errcode"):
            raise HTTPException(status_code=400, detail=userinfo_res.get("errmsg") or "Wechat userinfo failed")

    profile = {
        "appid": appid,
        "openid": userinfo_res.get("openid") or token_res.get("openid"),
        "unionid": userinfo_res.get("unionid") or token_res.get("unionid"),
        "nickname": userinfo_res.get("nickname"),
        "avatar_url": userinfo_res.get("headimgurl"),
        "province": userinfo_res.get("province"),
        "city": userinfo_res.get("city"),
        "country": userinfo_res.get("country"),
    }
    if activity_id and profile.get("openid"):
        _upsert_audience(db, request, WechatTrackRequest(activity_id=activity_id, **profile))
    return profile


@router.post("/wechat/track")
def public_track_wechat_user(
    data: WechatTrackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    audience = _upsert_audience(db, request, data)
    return {"message": "tracked", "audience_id": audience.id}


@router.get("/activities")
def public_list_activities(db: Session = Depends(get_db)):
    activities = (
        db.query(Activity)
        .filter(Activity.status == ActivityStatus.ACTIVE)
        .order_by(Activity.start_time.desc(), Activity.event_date.desc(), Activity.created_at.desc())
        .all()
    )
    result = []
    for activity in activities:
        ready_program_count = db.query(Program).filter(
            Program.activity_id == activity.id,
            Program.ready_status == ReadyStatus.READY,
        ).count()
        photo_count = db.query(Photo).filter(Photo.activity_id == activity.id).count()
        share_config = _load_json_setting(db, f"activity_{activity.id}_share_config")
        result.append({
            "id": activity.id,
            "name": activity.name,
            "description": activity.description,
            "event_date": activity.event_date.isoformat() if activity.event_date else None,
            "start_time": str(activity.start_time) if activity.start_time else None,
            "end_time": str(activity.end_time) if activity.end_time else None,
            "venue": activity.venue,
            "cover_image": share_config.get("coverUrl") or activity.cover_image,
            "program_count": ready_program_count,
            "photo_count": photo_count,
        })
    return result


@router.get("/activities/{activity_id}")
def public_get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    ready_program_count = db.query(Program).filter(
        Program.activity_id == activity.id,
        Program.ready_status == ReadyStatus.READY,
    ).count()
    photo_count = db.query(Photo).filter(Photo.activity_id == activity.id).count()
    share_config = _load_json_setting(db, f"activity_{activity.id}_share_config")
    return {
        "id": activity.id,
        "name": activity.name,
        "description": activity.description,
        "event_date": activity.event_date.isoformat() if activity.event_date else None,
        "start_time": str(activity.start_time) if activity.start_time else None,
        "end_time": str(activity.end_time) if activity.end_time else None,
        "venue": activity.venue,
        "cover_image": share_config.get("coverUrl") or activity.cover_image,
        "share_config": share_config,
        "program_count": ready_program_count,
        "photo_count": photo_count,
    }


@router.get("/lobby/{activity_id}/short-videos")
def public_lobby_short_videos(activity_id: int, db: Session = Depends(get_db)):
    """Lobby player endpoint — returns all ready short videos for an activity, no auth required."""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    programs = (
        db.query(Program)
        .filter(
            Program.activity_id == activity_id,
            Program.short_video_status == "ready",
            Program.short_video_url.isnot(None),
        )
        .order_by(Program.updated_at.desc())
        .all()
    )
    return {
        "activity": {
            "id": activity.id,
            "name": activity.name,
            "venue": activity.venue,
            "event_date": activity.event_date.isoformat() if activity.event_date else None,
        },
        "videos": [
            {
                "program_id": p.id,
                "program_name": p.name,
                "sequence_number": p.sequence_number,
                "short_video_url": p.short_video_url,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in programs
        ],
    }


@router.get("/activities/{activity_id}/programs/search")
def public_search_activity_programs(
    activity_id: int,
    q: str = Query("", max_length=100),
    db: Session = Depends(get_db),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    keyword = q.strip()
    query = db.query(Program).filter(Program.activity_id == activity_id)
    if keyword:
        if keyword.isdigit():
            query = query.filter(
                (Program.sequence_number == int(keyword)) | Program.name.contains(keyword)
            )
        else:
            query = query.filter(Program.name.contains(keyword))
    programs = query.order_by(Program.sequence_number.asc()).limit(200).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "sequence_number": item.sequence_number,
            "access_token": item.access_token,
            "photo_count": item.photo_count,
            "video_status": item.video_status.value,
            "ready_status": item.ready_status.value,
            "recorded_at": item.start_time.isoformat() if item.start_time else None,
            "program_url": build_public_url(db, f"/p/{item.access_token}"),
        }
        for item in programs
    ]


@router.get("/programs/search")
def public_search_programs(
    activity_name: Optional[str] = Query(None, max_length=200, description="活动名称（模糊匹配）"),
    activity_date: Optional[str] = Query(None, description="活动日期，格式 YYYY-MM-DD"),
    q: Optional[str] = Query(None, max_length=100, description="节目号或节目名"),
    db: Session = Depends(get_db),
):
    """
    跨活动节目搜索接口，供 COZE 智能体使用。
    支持通过活动名称/日期 + 节目号/节目名组合筛选。
    至少需要提供 q 参数（节目号或节目名）。
    """
    keyword = (q or "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="请提供节目号或节目名搜索关键词（q 参数）")

    # Build activity filter
    activity_query = db.query(Activity)
    has_activity_filter = False

    if activity_name:
        has_activity_filter = True
        activity_query = activity_query.filter(Activity.name.contains(activity_name.strip()))

    if activity_date:
        has_activity_filter = True
        try:
            from datetime import datetime as dt
            parsed_date = dt.strptime(activity_date, "%Y-%m-%d").date()
            activity_query = activity_query.filter(Activity.event_date == parsed_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="activity_date 格式错误，请使用 YYYY-MM-DD")

    activities = activity_query.all()
    if has_activity_filter and not activities:
        return []

    activity_ids = [a.id for a in activities] if has_activity_filter else None

    # Build program query
    program_query = db.query(Program).filter(Program.ready_status == ReadyStatus.READY)

    if activity_ids is not None:
        program_query = program_query.filter(Program.activity_id.in_(activity_ids))

    if keyword.isdigit():
        program_query = program_query.filter(
            (Program.sequence_number == int(keyword)) | Program.name.contains(keyword)
        )
    else:
        program_query = program_query.filter(Program.name.contains(keyword))

    programs = program_query.order_by(Program.sequence_number.asc()).limit(50).all()

    # Enrich with activity info
    activity_map = {a.id: a for a in db.query(Activity).all()}
    result = []
    for item in programs:
        act = activity_map.get(item.activity_id)
        result.append({
            "id": item.id,
            "name": item.name,
            "sequence_number": item.sequence_number,
            "access_token": item.access_token,
            "photo_count": item.photo_count,
            "video_status": item.video_status.value,
            "activity_id": item.activity_id,
            "activity_name": act.name if act else "",
            "activity_event_date": act.event_date.isoformat() if act and act.event_date else None,
            "activity_venue": act.venue if act else None,
        })
    return result


@router.get("/programs/{token}", response_model=ProgramPublicOut)
def public_get_program(
    token: str,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    is_admin = _check_admin_token(credentials)
    return _get_program_by_token_or_404(token, db, is_admin)


@router.get("/programs/{token}/photos", response_model=List[PhotoListOut])
def public_list_photos(
    token: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    is_admin = _check_admin_token(credentials)
    program = _get_program_by_token_or_404(token, db, is_admin)

    photos = (
        db.query(Photo)
        .filter(Photo.program_id == program.id)
        .order_by(Photo.shoot_time)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return photos


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


def _active_print_template(template: dict) -> dict:
    templates = template.get("templates")
    if not isinstance(templates, list) or not templates:
        return {}
    active_id = str(template.get("activeTemplateId") or "")
    if active_id:
        for item in templates:
            if isinstance(item, dict) and str(item.get("id") or "") == active_id:
                return item
    return templates[0] if isinstance(templates[0], dict) else {}


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


@router.post("/programs/{token}/photos/{photo_id}/print")
def public_create_print_record(
    token: str,
    photo_id: int,
    data: PublicPrintRequest,
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    is_admin = _check_admin_token(credentials)
    program = _get_program_by_token_or_404(token, db, is_admin)
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.program_id == program.id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    template = _load_activity_print_template(db, program.activity_id)
    user_identifier = data.user_identifier
    if not user_identifier:
        user_identifier = request.client.host if request.client else "public"

    import json

    # 检查蓝阔云打印是否启用
    from app.utils.lankuo_client import get_effective_lankuo_config
    from app.utils.print_dispatcher import should_dispatch_lankuo
    lankuo_cfg = get_effective_lankuo_config(db, program.activity_id)
    dispatch_lankuo = should_dispatch_lankuo(db, lankuo_cfg, program.activity_id)
    initial_status = "queued"

    record = PrintRecord(
        activity_id=program.activity_id,
        program_id=program.id,
        photo_id=photo.id,
        user_identifier=user_identifier,
        user_name=data.user_name or "公开页用户",
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


# ============================================================
# 公开接口：装饰素材列表
# ============================================================

@router.get("/materials")
def public_list_materials(
    type: Optional[str] = Query(None, description="素材类型：background / frame / sticker"),
    category: Optional[str] = Query(None, description="素材分类"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    公开素材列表，供前端画布编辑器调用
    仅返回 is_active=True 的素材
    """
    from app.models import DecorationMaterial

    query = db.query(DecorationMaterial).filter(DecorationMaterial.is_active == True)
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
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============================================================
# 公开接口：字体列表
# ============================================================

BUILT_IN_FONTS = [
    {"name": "思源黑体", "family": "Noto Sans SC", "weight": "normal"},
    {"name": "思源黑体粗体", "family": "Noto Sans SC", "weight": "bold"},
    {"name": "思源宋体", "family": "Noto Serif SC", "weight": "normal"},
    {"name": "思源宋体粗体", "family": "Noto Serif SC", "weight": "bold"},
    {"name": "站酷高端黑", "family": "ZCOOL XiaoWei", "weight": "normal"},
    {"name": "站酷快乐体", "family": "ZCOOL QingKe HuangYou", "weight": "normal"},
    {"name": "阿里巴巴普惠体", "family": "Alibaba PuHuiTi", "weight": "normal"},
    {"name": "阿里巴巴普惠体粗体", "family": "Alibaba PuHuiTi", "weight": "bold"},
]


@router.get("/fonts")
def public_list_fonts():
    """返回前端可用的字体列表（预装免费字体）"""
    return {"fonts": BUILT_IN_FONTS}


@router.get("/canvas-config/{activity_id}")
def public_canvas_config(activity_id: int, db: Session = Depends(get_db)):
    """获取画布编辑器配置（从活动打印模板读取）"""
    template = _load_activity_print_template(db, activity_id)
    active = _active_print_template(template)
    photo_slots = active.get("photoSlots")
    if not isinstance(photo_slots, list):
        photo_slots = template.get("photoSlots") if isinstance(template.get("photoSlots"), list) else []
    return {
        "templateName": active.get("name") or template.get("templateName") or "",
        "paperSize": _activity_template_paper_size(template),
        "canvasWidth": active.get("width") or template.get("canvasWidth", 800),
        "canvasHeight": active.get("height") or template.get("canvasHeight", 600),
        "photoInitX": template.get("photoInitX", 50),
        "photoInitY": template.get("photoInitY", 50),
        "photoInitScale": template.get("photoInitScale", 100),
        "photoMargin": template.get("photoMargin", 20),
        "photoSlots": photo_slots,
        "canvasJson": active.get("canvasJson"),
    }


# ============================================================
# 公开接口：画布打印（含额度检查）
# ============================================================

class CanvasPrintRequest(BaseModel):
    copies: int = Field(1, ge=1, le=99)
    openid: Optional[str] = None
    nickname: Optional[str] = None
    canvas_json: Optional[str] = Field(None, description="fabric.js 画布 JSON 数据")
    canvas_image: Optional[str] = Field(None, description="画布渲染图片（base64或URL）")
    canvas_width: Optional[int] = None
    canvas_height: Optional[int] = None
    template_name: Optional[str] = None
    paper_size: Optional[str] = None


def _check_and_set_payment_status(db: Session, record: PrintRecord, openid: str) -> str:
    """
    检查用户打印额度，设置 payment_status
    返回 payment_status：free / pending
    仅统计已确认的记录（free/paid），排除当前记录本身
    """
    activity_settings = get_activity_print_settings(db, record.activity_id)
    free_quota = int(activity_settings.get("print_free_quota", 2))
    print_price = int(activity_settings.get("print_price", 100))
    pay_enabled = False
    try:
        setting_pay = db.query(SystemSettings).filter(
            SystemSettings.key == "wechat_pay_enabled"
        ).first()
        if setting_pay and setting_pay.value == "true":
            pay_enabled = True
    except Exception:
        pass

    # 仅统计已确认的打印记录（排除当前记录和 pending/refunded 状态）
    used_count = db.query(PrintRecord).filter(
        PrintRecord.activity_id == record.activity_id,
        PrintRecord.user_identifier == openid,
        PrintRecord.id != record.id,
        PrintRecord.payment_status.in_(["free", "paid"]),
    ).count()

    if used_count < free_quota or not pay_enabled or print_price <= 0:
        record.payment_status = "free"
        record.payment_amount = 0
        return "free"
    else:
        record.payment_status = "pending"
        record.payment_amount = print_price
        return "pending"


@router.post("/programs/{token}/photos/{photo_id}/canvas-print")
async def public_canvas_print(
    token: str,
    photo_id: int,
    data: CanvasPrintRequest,
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    画布打印接口：接收 fabric.js 画布数据，创建打印记录
    支持免费额度检查，超额返回 payment_status=pending
    如果蓝阔云打印已启用，自动提交打印任务到云打印机
    """
    import json
    import base64

    is_admin = _check_admin_token(credentials)
    program = _get_program_by_token_or_404(token, db, is_admin)

    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.program_id == program.id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    openid = data.openid
    if not openid:
        openid = request.client.host if request.client else "public"

    # 存储画布 JSON（包含 canvas_image 引用）
    canvas_json_str = None
    if data.canvas_json:
        try:
            canvas_data = json.loads(data.canvas_json)
            # 将 canvas_image 一并存入 canvas 数据中
            if data.canvas_image:
                canvas_data["_canvas_image"] = data.canvas_image
            if data.canvas_width:
                canvas_data["_canvas_width"] = data.canvas_width
            if data.canvas_height:
                canvas_data["_canvas_height"] = data.canvas_height
            canvas_json_str = json.dumps(canvas_data, ensure_ascii=False)
        except Exception:
            canvas_json_str = data.canvas_json
    elif data.canvas_image:
        # 仅传了图片没有 JSON
        canvas_json_str = json.dumps({
            "_canvas_image": data.canvas_image,
            "_canvas_width": data.canvas_width,
            "_canvas_height": data.canvas_height,
        }, ensure_ascii=False)

    # 检查蓝阔云打印是否启用
    from app.utils.lankuo_client import get_effective_lankuo_config
    from app.utils.print_dispatcher import should_dispatch_lankuo
    lankuo_cfg = get_effective_lankuo_config(db, program.activity_id)
    dispatch_lankuo = should_dispatch_lankuo(db, lankuo_cfg, program.activity_id)
    initial_status = "queued"

    record = PrintRecord(
        activity_id=program.activity_id,
        program_id=program.id,
        photo_id=photo.id,
        user_identifier=openid,
        user_name=data.nickname or "公开页用户",
        template_name=data.template_name or "画布编辑器",
        paper_size=_activity_template_paper_size(_load_activity_print_template(db, program.activity_id)),
        copies=data.copies,
        status=initial_status,
        print_payload_json=canvas_json_str,
    )
    db.add(record)
    db.flush()

    # 额度检查并设置 payment_status
    payment_status = _check_and_set_payment_status(db, record, openid)
    pay_data = None
    if payment_status == "pending":
        from app.utils.wechat_pay import create_jsapi_payment

        pay_data = await create_jsapi_payment(db, record, openid)
    db.commit()
    db.refresh(record)
    if pay_data:
        return {
            "message": "payment required",
            "record_id": record.id,
            "payment_status": payment_status,
            "payment_status_display": "pending wechat pay",
            **pay_data,
        }

    # 如果蓝阔云打印已启用，异步提交打印任务
    if dispatch_lankuo:
        from app.utils.print_dispatcher import dispatch_print_task
        dispatch_print_task(record.id, lankuo_cfg, db)

    return {
        "message": "print queued",
        "record_id": record.id,
        "payment_status": payment_status,
        "payment_status_display": "免费打印" if payment_status == "free" else "待支付（功能升级中）",
    }


# ============================================================
# 公开接口：蓝阔云打印回调
# ============================================================

def _pick_callback_value(payload: dict, *keys: str):
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _normalize_lankuo_callback_status(value) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip().upper()
    if text in {"2", "DONE", "SUCCESS", "SUCCEEDED", "FINISHED", "COMPLETED", "OK"}:
        return "success"
    if text in {"3", "ERROR", "FAILED", "FAIL", "CANCEL", "CANCELLED", "CANCELED"}:
        return "failed"
    if text in {"1", "PRINTING", "SENDING", "PROCESSING", "RUNNING"}:
        return "printing"
    if text in {"0", "WAITING", "PENDING", "QUEUED"}:
        return "waiting"
    return None


def _callback_error_message(payload: dict) -> str:
    value = _pick_callback_value(
        payload,
        "msg",
        "message",
        "error",
        "errorMsg",
        "error_msg",
        "task_result",
        "result",
    )
    return (str(value) if value is not None else "print failed")[:500]


@router.api_route("/print-callback", methods=["GET", "POST"])
async def lankuo_print_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive Lankuo print result callbacks and update the user's print record."""
    import json
    from datetime import datetime

    logger = logging.getLogger(__name__)
    payload = dict(request.query_params)

    if request.method == "POST":
        content_type = request.headers.get("content-type", "").lower()
        try:
            if "application/json" in content_type:
                body = await request.json()
                if isinstance(body, dict):
                    payload.update(body)
            elif "form" in content_type:
                form = await request.form()
                payload.update(dict(form))
            else:
                raw_body = (await request.body()).decode("utf-8", "ignore").strip()
                if raw_body:
                    try:
                        body = json.loads(raw_body)
                        if isinstance(body, dict):
                            payload.update(body)
                        else:
                            payload["_raw_body"] = raw_body[:1000]
                    except Exception:
                        payload["_raw_body"] = raw_body[:1000]
        except Exception as exc:
            logger.warning("Failed to parse Lankuo callback payload: %s", exc)

    logger.info(
        "Lankuo print callback payload: %s",
        {key: str(value)[:500] for key, value in payload.items()},
    )

    task_id = _pick_callback_value(payload, "taskId", "task_id", "taskid", "taskID", "id")
    if not task_id:
        return {"code": 0, "msg": "missing task id"}

    record = db.query(PrintRecord).filter(PrintRecord.task_id == str(task_id)).first()
    if not record:
        logger.warning("Lankuo callback record not found: task_id=%s", task_id)
        return {"code": 0, "msg": "record not found", "task_id": str(task_id)}

    status_value = _pick_callback_value(
        payload,
        "status",
        "task_state",
        "taskState",
        "state",
        "printStatus",
        "print_status",
    )
    next_status = _normalize_lankuo_callback_status(status_value)

    if next_status == "success":
        record.status = "success"
        record.printed_at = datetime.now()
        record.error_msg = None
    elif next_status == "failed":
        record.status = "failed"
        record.error_msg = _callback_error_message(payload)
    elif next_status == "printing":
        if record.status != "success":
            record.status = "printing"
    elif next_status == "waiting":
        if record.status not in {"success", "failed"}:
            record.status = "printing"
    else:
        logger.warning(
            "Lankuo callback has unknown status: task_id=%s status=%s",
            task_id,
            status_value,
        )

    db.commit()
    return {"code": 0, "msg": "ok", "record_id": record.id, "status": record.status}


class LankuoCallbackRequest(BaseModel):
    """蓝阔云打印回调请求体"""
    taskId: Optional[str] = None
    status: Optional[int] = None  # 0=等待, 1=打印中, 2=完成, 3=失败
    msg: Optional[str] = None
    deviceId: Optional[str] = None


@router.post("/print-callback-legacy")
def lankuo_print_callback_legacy(
    data: LankuoCallbackRequest,
    db: Session = Depends(get_db),
):
    """
    蓝阔云打印结果回调
    蓝阔打印完成后会回调此接口通知结果
    """
    logger = logging.getLogger(__name__)

    if not data.taskId:
        return {"code": 0, "msg": "ok"}

    # 根据 taskId 查找打印记录
    record = db.query(PrintRecord).filter(
        PrintRecord.task_id == str(data.taskId)
    ).first()

    if not record:
        logger.warning(f"蓝阔回调: 未找到 taskId={data.taskId} 的打印记录")
        return {"code": 0, "msg": "record not found"}

    if data.status == 2:
        record.status = "success"
        from datetime import datetime
        record.printed_at = datetime.now()
        logger.info(f"蓝阔回调: 打印记录 {record.id} 打印完成 (taskId={data.taskId})")
    elif data.status == 3:
        record.status = "failed"
        record.error_msg = (data.msg or "打印失败")[:500]
        logger.warning(f"蓝阔回调: 打印记录 {record.id} 打印失败 (taskId={data.taskId}): {data.msg}")
    elif data.status == 1:
        record.status = "printing"
        logger.info(f"蓝阔回调: 打印记录 {record.id} 正在打印 (taskId={data.taskId})")
    # status=0 继续等待，不更新

    db.commit()
    return {"code": 0, "msg": "ok"}


# ============================================================
# 公开接口：用户个人中心记录
# ============================================================

@router.get("/user/records")
def public_user_records(
    openid: str = Query(..., description="微信用户openid"),
    record_type: Optional[str] = Query(None, description="download / print，筛选类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    查询用户在某活动下的下载记录和打印记录
    用于个人中心页面展示
    """
    from app.models import DownloadRecord

    result = {"downloads": [], "prints": []}
    total_downloads = 0
    total_prints = 0

    if record_type is None or record_type == "download":
        dl_query = db.query(DownloadRecord).filter(DownloadRecord.user_identifier == openid)
        total_downloads = dl_query.count()
        dl_records = (
            dl_query.order_by(DownloadRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        result["downloads"] = [
            {
                "id": r.id,
                "photo_id": r.photo_id,
                "photo_url": r.photo_url,
                "program_name": r.program_name,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in dl_records
        ]

    if record_type is None or record_type == "print":
        print_query = db.query(PrintRecord).filter(PrintRecord.user_identifier == openid)
        total_prints = print_query.count()
        print_records = (
            print_query.order_by(PrintRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        result["prints"] = [
            {
                "id": r.id,
                "photo_id": r.photo_id,
                "template_name": r.template_name,
                "paper_size": r.paper_size,
                "copies": r.copies,
                "status": r.status,
                "payment_status": r.payment_status,
                "payment_amount": r.payment_amount,
                "created_at": str(r.created_at) if r.created_at else None,
                "printed_at": str(r.printed_at) if r.printed_at else None,
            }
            for r in print_records
        ]

    return {
        **result,
        "total_downloads": total_downloads,
        "total_prints": total_prints,
        "page": page,
        "page_size": page_size,
    }


@router.get("/user/admin-entry")
def public_user_admin_entry(
    openid: str = Query(..., description="微信用户openid"),
    db: Session = Depends(get_db),
):
    """Return an admin token and landing page when a WeChat user has a management role."""
    user = db.query(AppUser).filter(AppUser.openid == openid, AppUser.is_deleted.is_(False)).first()
    if not user or user.is_blacklisted:
        return {"enabled": False}

    permissions, activity_ids, role_codes = user_permissions(db, openid)
    if not permissions:
        return {"enabled": False}

    if "print.manage" in permissions and "activity.manage" not in permissions:
        management_url = "/m/print-admin"
    else:
        management_url = "/m/activity-admin"

    token = create_access_token({
        "sub": openid,
        "name": user.nickname or "微信管理员",
        "role_codes": role_codes,
        "permissions": sorted(permissions),
        "activity_ids": sorted(activity_ids),
    })
    return {
        "enabled": True,
        "access_token": token,
        "token_type": "bearer",
        "username": user.nickname or "微信管理员",
        "role_codes": role_codes,
        "permissions": sorted(permissions),
        "activity_ids": sorted(activity_ids),
        "management_url": management_url,
    }


@router.delete("/user/print-records/{record_id}")
def delete_user_print_record(
    record_id: int,
    openid: str = Query(..., description="微信用户openid"),
    db: Session = Depends(get_db),
):
    """删除用户自己的打印记录（仅限 failed / queued 状态）"""
    record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.user_identifier != openid:
        raise HTTPException(status_code=403, detail="无权删除此记录")
    if record.status not in ("failed", "queued"):
        raise HTTPException(status_code=400, detail="仅失败或排队中的打印记录可以删除")

    db.delete(record)
    db.commit()
    return {"message": "已删除", "id": record_id}
