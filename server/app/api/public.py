from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Activity, ActivityStatus, Audience, Program, Photo, PrintRecord, ReadyStatus, SystemSettings
from app.schemas.photo import PhotoListOut
from app.schemas.activity import ProgramPublicOut
from app.utils.auth import decode_token
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
    query = db.query(Program).filter(
        Program.activity_id == activity_id,
        Program.ready_status == ReadyStatus.READY,
    )
    if keyword:
        if keyword.isdigit():
            query = query.filter(
                (Program.sequence_number == int(keyword)) | Program.name.contains(keyword)
            )
        else:
            query = query.filter(Program.name.contains(keyword))
    programs = query.order_by(Program.sequence_number.asc()).limit(30).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "sequence_number": item.sequence_number,
            "access_token": item.access_token,
            "photo_count": item.photo_count,
            "video_status": item.video_status.value,
        }
        for item in programs
    ]


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

    record = PrintRecord(
        activity_id=program.activity_id,
        program_id=program.id,
        photo_id=photo.id,
        user_identifier=user_identifier,
        user_name=data.user_name or "公开页用户",
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
