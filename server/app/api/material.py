from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.auth import get_current_user
from app.utils.rbac import require_permission
from app.models import SystemSettings, PrintRecord, DecorationMaterial

router = APIRouter()


# ============================================================
# 打印配额配置键名（与 payment.py 保持一致）
# ============================================================
PRINT_FREE_QUOTA_KEY = "print_free_quota"
PRINT_PRICE_KEY = "print_price"
WECHAT_PAY_ENABLED_KEY = "wechat_pay_enabled"
WECHAT_PAY_MCHID_KEY = "wechat_pay_mchid"
WECHAT_PAY_API_KEY_KEY = "wechat_pay_api_key"
WECHAT_PAY_NOTIFY_URL_KEY = "wechat_pay_notify_url"
LANKUO_PRINT_CONFIG_KEY = "lankuo_print_config"
PRINT_RENDER_MODE_KEY = "print_render_mode"
PRINT_RENDER_MULTIPLIER_KEY = "print_render_multiplier"
PRINT_DISPATCH_MODE_KEY = "print_dispatch_mode"
PRINT_RENDER_MODE_FRONTEND = "frontend"
PRINT_RENDER_MODE_SERVER = "server"
PRINT_DISPATCH_MODE_LANKUO = "lankuo"
PRINT_DISPATCH_MODE_LOCAL_CLIENT = "local_client"
DEFAULT_PRINT_RENDER_MULTIPLIER = 1

DEFAULT_FREE_QUOTA = 2
DEFAULT_PRINT_PRICE = 100  # 1元（单位：分）
DEFAULT_LANKUO_PRINT_CONFIG = {
    "enabled": False,
    "provider": "lankuo",
    "providerName": "蓝阔（链科云打印 v3）",
    "apiBaseUrl": "https://cloud.liankenet.com",
    "ApiKey": "",
    "deviceId": "",
    "deviceKey": "",
    "devicePort": "1",
    "printerType": "1",
    "printerModel": "",
    "targetIp": "",
    "dmPaperSize": "9",
    "dmOrientation": "1",
    "dmCopies": 1,
    "dmColor": "2",
    "dmDuplex": "1",
    "dmDefaultSource": "",
    "dmMediaType": "",
    "dmPaperLength": 300,
    "dmPaperWidth": 200,
    "dmPrintQuality": "",
    "jpScale": "fit",
    "jpAutoAlign": "z5",
    "jpPageRange": "",
    "htmlKernel": "chrometopdf",
    "callbackUrl": "",
    "reportDeviceStatus": True,
    "reportPrinterStatus": True,
    "errLimitNum": 30,
    "pdfRev": False,
    "jpAutoRotate": False,
}


def _get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting and setting.value is not None else default


def _set_setting(db: Session, key: str, value: str, description: str = "") -> None:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        setting = SystemSettings(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description:
            setting.description = description
    db.commit()


def _normalize_lankuo_print_config(config: Optional[dict]) -> dict:
    cleaned = {**DEFAULT_LANKUO_PRINT_CONFIG, **(config or {})}
    cleaned.pop("urlFileExt", None)
    cleaned["provider"] = "lankuo"
    cleaned["providerName"] = "蓝阔（链科云打印 v3）"
    return cleaned


def _get_lankuo_print_config(db: Session) -> dict:
    import json

    raw = _get_setting(db, LANKUO_PRINT_CONFIG_KEY, "")
    if not raw:
        return _normalize_lankuo_print_config({})
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {}
    return _normalize_lankuo_print_config(parsed)


def _get_print_render_multiplier(db: Session) -> int:
    try:
        value = int(_get_setting(db, PRINT_RENDER_MULTIPLIER_KEY, str(DEFAULT_PRINT_RENDER_MULTIPLIER)))
    except (TypeError, ValueError):
        value = DEFAULT_PRINT_RENDER_MULTIPLIER
    return min(max(value, 1), 3)


# ============================================================
# 管理后台接口：打印设置
# ============================================================

class PrintSettingsOut(BaseModel):
    print_free_quota: int
    print_price: int
    wechat_pay_enabled: bool
    wechat_pay_mchid: str
    wechat_pay_api_key: str
    wechat_pay_notify_url: str
    print_render_mode: str = PRINT_RENDER_MODE_FRONTEND
    print_render_multiplier: int = DEFAULT_PRINT_RENDER_MULTIPLIER
    print_dispatch_mode: str = PRINT_DISPATCH_MODE_LANKUO
    lankuo_print_config: dict = Field(default_factory=dict)


class PrintSettingsUpdate(BaseModel):
    print_free_quota: Optional[int] = None
    print_price: Optional[int] = None
    wechat_pay_enabled: Optional[bool] = None
    wechat_pay_mchid: Optional[str] = None
    wechat_pay_api_key: Optional[str] = None
    wechat_pay_notify_url: Optional[str] = None
    print_render_mode: Optional[str] = None
    print_render_multiplier: Optional[int] = Field(None, ge=1, le=3)
    print_dispatch_mode: Optional[str] = None
    lankuo_print_config: Optional[dict] = None


@router.get("/settings", response_model=PrintSettingsOut)
def get_print_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "print.manage")
    """获取打印设置"""
    return PrintSettingsOut(
        print_free_quota=int(_get_setting(db, PRINT_FREE_QUOTA_KEY, str(DEFAULT_FREE_QUOTA))),
        print_price=int(_get_setting(db, PRINT_PRICE_KEY, str(DEFAULT_PRINT_PRICE))),
        wechat_pay_enabled=_get_setting(db, WECHAT_PAY_ENABLED_KEY, "false") == "true",
        wechat_pay_mchid=_get_setting(db, WECHAT_PAY_MCHID_KEY, ""),
        wechat_pay_api_key="",  # 不返回密钥，只用于配置
        wechat_pay_notify_url=_get_setting(db, WECHAT_PAY_NOTIFY_URL_KEY, ""),
        print_render_mode=_get_setting(db, PRINT_RENDER_MODE_KEY, PRINT_RENDER_MODE_FRONTEND),
        print_render_multiplier=_get_print_render_multiplier(db),
        print_dispatch_mode=_get_setting(db, PRINT_DISPATCH_MODE_KEY, PRINT_DISPATCH_MODE_LANKUO),
        lankuo_print_config=_get_lankuo_print_config(db),
    )


@router.put("/settings", response_model=PrintSettingsOut)
def update_print_settings(
    data: PrintSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "print.manage")
    """更新打印设置"""
    if data.print_free_quota is not None:
        _set_setting(db, PRINT_FREE_QUOTA_KEY, str(data.print_free_quota), "每用户每活动免费打印张数")
    if data.print_price is not None:
        _set_setting(db, PRINT_PRICE_KEY, str(data.print_price), "超额后单张打印价格（单位：分）")
    if data.wechat_pay_enabled is not None:
        _set_setting(db, WECHAT_PAY_ENABLED_KEY, "true" if data.wechat_pay_enabled else "false", "是否启用微信支付")
    if data.wechat_pay_mchid is not None:
        _set_setting(db, WECHAT_PAY_MCHID_KEY, data.wechat_pay_mchid, "微信支付商户号")
    if data.wechat_pay_api_key is not None:
        _set_setting(db, WECHAT_PAY_API_KEY_KEY, data.wechat_pay_api_key, "微信支付API密钥")
    if data.wechat_pay_notify_url is not None:
        _set_setting(db, WECHAT_PAY_NOTIFY_URL_KEY, data.wechat_pay_notify_url, "微信支付回调URL")
    if data.print_render_mode is not None:
        render_mode = data.print_render_mode if data.print_render_mode in {PRINT_RENDER_MODE_FRONTEND, PRINT_RENDER_MODE_SERVER} else PRINT_RENDER_MODE_FRONTEND
        _set_setting(db, PRINT_RENDER_MODE_KEY, render_mode, "打印图片合成方式")
    if data.print_dispatch_mode is not None:
        dispatch_mode = data.print_dispatch_mode if data.print_dispatch_mode in {PRINT_DISPATCH_MODE_LANKUO, PRINT_DISPATCH_MODE_LOCAL_CLIENT} else PRINT_DISPATCH_MODE_LANKUO
        _set_setting(db, PRINT_DISPATCH_MODE_KEY, dispatch_mode, "打印任务派发方式")
    if data.print_render_multiplier is not None:
        multiplier = min(max(int(data.print_render_multiplier), 1), 3)
        _set_setting(db, PRINT_RENDER_MULTIPLIER_KEY, str(multiplier), "服务端打印合成图倍率")
    if data.lankuo_print_config is not None:
        import json
        current_config = _get_lankuo_print_config(db)
        next_config = _normalize_lankuo_print_config({**current_config, **data.lankuo_print_config})
        _set_setting(
            db,
            LANKUO_PRINT_CONFIG_KEY,
            json.dumps(next_config, ensure_ascii=False),
            "蓝阔云打印配置",
        )
    return get_print_settings(db, current_user)


# ============================================================
# 管理后台接口：素材上传
# ============================================================

@router.post("/upload")
async def upload_material_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "material.manage")
    """上传素材文件，返回存储URL"""
    from app.utils.cloud_assets import upload_image_to_cloud

    return await upload_image_to_cloud(file, prefix="decoration-materials")


# ============================================================
# 管理后台接口：打印统计
# ============================================================

@router.get("/stats")
def get_print_stats(
    activity_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "print.manage")
    """获取打印统计数据"""
    query = db.query(PrintRecord)
    if activity_id:
        query = query.filter(PrintRecord.activity_id == activity_id)

    total = query.count()
    free_count = query.filter(PrintRecord.payment_status == "free").count()
    paid_count = query.filter(PrintRecord.payment_status == "paid").count()
    pending_count = query.filter(PrintRecord.payment_status == "pending").count()
    refunded_count = query.filter(PrintRecord.payment_status == "refunded").count()

    # 计算付费收入
    paid_records = query.filter(
        PrintRecord.payment_status == "paid",
        PrintRecord.payment_amount.isnot(None),
    ).all()
    total_revenue = sum(r.payment_amount or 0 for r in paid_records)

    return {
        "total": total,
        "free_count": free_count,
        "paid_count": paid_count,
        "pending_count": pending_count,
        "refunded_count": refunded_count,
        "total_revenue": total_revenue,  # 单位：分
    }
