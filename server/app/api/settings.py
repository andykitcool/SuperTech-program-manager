import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.utils.auth import get_current_user
from app.utils.rbac import require_activity_access, require_permission
from app.models import SystemSettings
from app.schemas.settings import SettingsOut, SettingsUpdate, StorageTestResult, StorageTestRequest

router = APIRouter()


WECHAT_PAY_ENABLED_KEY = "wechat_pay_enabled"
WECHAT_PAY_APPID_KEY = "wechat_pay_appid"
WECHAT_PAY_MCHID_KEY = "wechat_pay_mchid"
WECHAT_PAY_API_KEY_KEY = "wechat_pay_api_key"
WECHAT_PAY_API_V3_KEY_KEY = "wechat_pay_api_v3_key"
WECHAT_PAY_MERCHANT_SERIAL_NO_KEY = "wechat_pay_merchant_serial_no"
WECHAT_PAY_PRIVATE_KEY_KEY = "wechat_pay_private_key"
WECHAT_PAY_NOTIFY_URL_KEY = "wechat_pay_notify_url"
WECHAT_PAY_REFUND_NOTIFY_URL_KEY = "wechat_pay_refund_notify_url"
WECHAT_PAY_DESCRIPTION_KEY = "wechat_pay_description"
LANKUO_PRINT_CONFIG_KEY = "lankuo_print_config"
LANKUO_PRINTER_PARAMS_CACHE_KEY = "lankuo_printer_params_cache"
ACTIVITY_PRINT_TEMPLATE_KEY_PATTERN = re.compile(r"^activity_(\d+)_print_template$")


class WechatPaySettingsOut(BaseModel):
    enabled: bool = False
    appid: str = ""
    mchid: str = ""
    api_key: str = ""
    api_v3_key: str = ""
    merchant_serial_no: str = ""
    private_key: str = ""
    notify_url: str = ""
    refund_notify_url: str = ""
    description: str = ""
    has_api_key: bool = False
    has_api_v3_key: bool = False
    has_private_key: bool = False


class WechatPaySettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    appid: Optional[str] = None
    mchid: Optional[str] = None
    api_key: Optional[str] = None
    api_v3_key: Optional[str] = None
    merchant_serial_no: Optional[str] = None
    private_key: Optional[str] = None
    notify_url: Optional[str] = None
    refund_notify_url: Optional[str] = None
    description: Optional[str] = None


class NetworkSettingsUpdate(BaseModel):
    domain: Optional[str] = None
    base_url: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    force_https: Optional[bool] = None
    ssl_cert_pem: Optional[str] = None
    ssl_key_pem: Optional[str] = None


def _load_json_value(value: str, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def _get_setting_value(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting and setting.value is not None else default


def _set_setting_value(db: Session, key: str, value: str, description: str = "") -> None:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        setting = SystemSettings(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description:
            setting.description = description


def _authorize_setting_key_access(db: Session, current_user: dict, key: str) -> None:
    match = ACTIVITY_PRINT_TEMPLATE_KEY_PATTERN.match(key)
    if match:
        require_activity_access(db, current_user, int(match.group(1)), "print.manage")
        return
    require_permission(current_user, "system.manage")


def _require_system_or_print_manage(current_user: dict) -> None:
    permissions = set(current_user.get("permissions") or [])
    role_codes = set(current_user.get("role_codes") or [])
    if (
        current_user.get("sub") == "admin"
        or "super_admin" in role_codes
        or "system.manage" in permissions
        or "print.manage" in permissions
    ):
        return
    raise HTTPException(status_code=403, detail="没有权限执行此操作")


def _load_lankuo_print_config(db: Session) -> dict:
    config = _load_json_value(_get_setting_value(db, LANKUO_PRINT_CONFIG_KEY, ""), {})
    if not isinstance(config, dict):
        config = {}
    config.pop("urlFileExt", None)
    config.setdefault("apiBaseUrl", "https://cloud.liankenet.com")
    config.setdefault("printerType", "1")
    return config


def _load_printer_params_cache(db: Session) -> dict:
    cache = _load_json_value(_get_setting_value(db, LANKUO_PRINTER_PARAMS_CACHE_KEY, ""), {})
    if not isinstance(cache, dict):
        cache = {}
    cache.setdefault("version", 1)
    cache.setdefault("params_by_model", {})
    return cache


def _save_printer_params_cache(db: Session, cache: dict) -> None:
    _set_setting_value(
        db,
        LANKUO_PRINTER_PARAMS_CACHE_KEY,
        json.dumps(cache, ensure_ascii=False),
        "蓝阔打印机参数缓存",
    )
    db.commit()


def _printer_model(printer: dict) -> str:
    return str(
        printer.get("driver_name")
        or printer.get("drivce_name")
        or printer.get("printer_name")
        or ""
    ).strip()


def _printer_is_online(printer: dict) -> bool:
    try:
        is_printer = int(printer.get("isPrinter", 0)) == 1
    except (TypeError, ValueError):
        is_printer = bool(printer.get("isPrinter"))
    try:
        driver_type = int(printer.get("driver_type", 0))
    except (TypeError, ValueError):
        driver_type = 0
    return is_printer and driver_type != 2


def _normalize_printer(printer: dict) -> dict:
    item = dict(printer or {})
    item["driver_name"] = _printer_model(item)
    item["is_online"] = _printer_is_online(item)
    state = str(item.get("printer_state") or "").strip()
    if not item["is_online"]:
        item["status_label"] = "不可用"
        item["status_level"] = "offline"
    elif state in {"idle", ""}:
        item["status_label"] = "在线"
        item["status_level"] = "online"
    elif state == "printing":
        item["status_label"] = "打印中"
        item["status_level"] = "busy"
    else:
        item["status_label"] = state
        item["status_level"] = "warning"
    return item


def _option_items(values) -> list[dict]:
    if not isinstance(values, dict):
        return []
    return [
        {"label": f"{label} ({value})", "value": str(value), "name": str(label)}
        for label, value in values.items()
    ]


async def _get_cached_printer_params(
    db: Session,
    client,
    printer_model: str,
    refresh: bool,
) -> tuple[dict, bool, Optional[str]]:
    if not printer_model:
        return {}, False, None

    cache = _load_printer_params_cache(db)
    params_by_model = cache.setdefault("params_by_model", {})
    cached = params_by_model.get(printer_model)
    if cached and not refresh:
        return cached.get("data") or {}, True, cached.get("cached_at")

    params = await client.get_printer_params(printer_model, use_cache=False)
    cached_at = datetime.now().isoformat(timespec="seconds")
    params_by_model[printer_model] = {
        "cached_at": cached_at,
        "data": params,
    }
    _save_printer_params_cache(db, cache)
    return params, False, cached_at


@router.get("", response_model=List[SettingsOut])
def list_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.manage")
    return db.query(SystemSettings).all()


@router.get("/wechat-pay", response_model=WechatPaySettingsOut)
def get_wechat_pay_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.manage")
    api_key = _get_setting_value(db, WECHAT_PAY_API_KEY_KEY, "")
    api_v3_key = _get_setting_value(db, WECHAT_PAY_API_V3_KEY_KEY, "")
    private_key = _get_setting_value(db, WECHAT_PAY_PRIVATE_KEY_KEY, "")
    return WechatPaySettingsOut(
        enabled=_get_setting_value(db, WECHAT_PAY_ENABLED_KEY, "false") == "true",
        appid=_get_setting_value(db, WECHAT_PAY_APPID_KEY, ""),
        mchid=_get_setting_value(db, WECHAT_PAY_MCHID_KEY, ""),
        notify_url=_get_setting_value(db, WECHAT_PAY_NOTIFY_URL_KEY, ""),
        refund_notify_url=_get_setting_value(db, WECHAT_PAY_REFUND_NOTIFY_URL_KEY, ""),
        merchant_serial_no=_get_setting_value(db, WECHAT_PAY_MERCHANT_SERIAL_NO_KEY, ""),
        description=_get_setting_value(db, WECHAT_PAY_DESCRIPTION_KEY, "照片打印"),
        has_api_key=bool(api_key),
        has_api_v3_key=bool(api_v3_key),
        has_private_key=bool(private_key),
    )


@router.put("/wechat-pay", response_model=WechatPaySettingsOut)
def update_wechat_pay_settings(
    data: WechatPaySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.manage")
    if data.enabled is not None:
        _set_setting_value(db, WECHAT_PAY_ENABLED_KEY, "true" if data.enabled else "false", "是否启用微信支付")
    if data.appid is not None:
        _set_setting_value(db, WECHAT_PAY_APPID_KEY, data.appid, "微信支付关联 AppID")
    if data.mchid is not None:
        _set_setting_value(db, WECHAT_PAY_MCHID_KEY, data.mchid, "微信支付商户号")
    if data.merchant_serial_no is not None:
        _set_setting_value(db, WECHAT_PAY_MERCHANT_SERIAL_NO_KEY, data.merchant_serial_no, "微信支付商户证书序列号")
    if data.notify_url is not None:
        _set_setting_value(db, WECHAT_PAY_NOTIFY_URL_KEY, data.notify_url, "微信支付回调URL")
    if data.refund_notify_url is not None:
        _set_setting_value(db, WECHAT_PAY_REFUND_NOTIFY_URL_KEY, data.refund_notify_url, "微信支付退款回调URL")
    if data.description is not None:
        _set_setting_value(db, WECHAT_PAY_DESCRIPTION_KEY, data.description, "微信支付订单描述")

    if data.api_key:
        _set_setting_value(db, WECHAT_PAY_API_KEY_KEY, data.api_key, "微信支付API密钥")
    if data.api_v3_key:
        _set_setting_value(db, WECHAT_PAY_API_V3_KEY_KEY, data.api_v3_key, "微信支付API v3密钥")
    if data.private_key:
        _set_setting_value(db, WECHAT_PAY_PRIVATE_KEY_KEY, data.private_key, "微信支付商户私钥")

    db.commit()
    return get_wechat_pay_settings(db, current_user)


@router.get("/network")
def get_network_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.manage")
    from app.utils.network_settings import load_network_settings

    return load_network_settings(db)


@router.put("/network")
def update_network_settings(
    data: NetworkSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.manage")
    import logging
    from app.utils.network_settings import save_network_settings, save_ssl_files, write_nginx_ssl_config, reload_nginx

    logger = logging.getLogger(__name__)
    payload = data.model_dump(exclude_unset=True)

    try:
        if payload.get("ssl_cert_pem") or payload.get("ssl_key_pem"):
            save_ssl_files(payload.pop("ssl_cert_pem", None), payload.pop("ssl_key_pem", None))
        settings = save_network_settings(db, payload)
        write_nginx_ssl_config(settings)
        reload_nginx()
        return settings
    except PermissionError as e:
        logger.error(f"Permission denied writing SSL/nginx files: {e}")
        raise HTTPException(status_code=500, detail=f"文件写入权限不足: {e}")
    except OSError as e:
        logger.error(f"IO error writing SSL/nginx files: {e}")
        raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")
    except Exception as e:
        logger.error(f"Failed to save network settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存网络设置失败: {e}")


@router.get("/lankuo/printers")
async def get_lankuo_printers(
    printer_model: Optional[str] = Query(None),
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_system_or_print_manage(current_user)

    from app.utils.lankuo_client import LankuoClient, LankuoPrintError

    config = _load_lankuo_print_config(db)
    missing = [
        key
        for key in ("ApiKey", "deviceId", "deviceKey")
        if not str(config.get(key) or "").strip()
    ]
    if missing:
        return {
            "configured": False,
            "missing": missing,
            "printers": [],
            "online_printers": [],
            "selected_printer": None,
            "selected_model": "",
            "printer_params": {},
            "params_cached": False,
            "params_cached_at": None,
            "media_type_options": [],
            "paper_options": [],
            "message": "请先配置 ApiKey、deviceId 和 deviceKey",
        }

    try:
        client = LankuoClient(config)
        printers = [_normalize_printer(item) for item in await client.get_printer_list(use_cache=False)]
    except LankuoPrintError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"获取蓝阔打印机列表失败: {exc}")

    online_printers = [item for item in printers if item.get("is_online")]
    configured_model = str(printer_model or config.get("printerModel") or "").strip()
    selected = next((item for item in online_printers if _printer_model(item) == configured_model), None)
    if not selected and len(online_printers) == 1:
        selected = online_printers[0]
    elif not selected and configured_model:
        selected = next((item for item in printers if _printer_model(item) == configured_model), None)
    elif not selected and online_printers:
        selected = online_printers[0]

    selected_model = _printer_model(selected or {}) if selected else configured_model
    printer_params = {}
    params_cached = False
    params_cached_at = None
    if selected_model:
        try:
            printer_params, params_cached, params_cached_at = await _get_cached_printer_params(
                db,
                client,
                selected_model,
                refresh,
            )
        except LankuoPrintError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"获取蓝阔打印机参数失败: {exc}")

    capabilities = printer_params.get("Capabilities") if isinstance(printer_params, dict) else {}
    media_type_options = _option_items((capabilities or {}).get("MediaTypes"))
    paper_options = _option_items((capabilities or {}).get("Papers"))

    return {
        "configured": True,
        "printers": printers,
        "online_printers": online_printers,
        "selected_printer": selected,
        "selected_model": selected_model,
        "printer_params": printer_params,
        "params_cached": params_cached,
        "params_cached_at": params_cached_at,
        "media_type_options": media_type_options,
        "paper_options": paper_options,
    }


@router.get("/{key}")
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _authorize_setting_key_access(db, current_user, key)
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        return {"id": 0, "key": key, "value": None, "description": None, "created_at": None, "updated_at": None}
    return setting


@router.put("/{key}", response_model=SettingsOut)
def update_setting(
    key: str,
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _authorize_setting_key_access(db, current_user, key)
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        setting = SystemSettings(key=key, value=data.value)
        db.add(setting)
    else:
        setting.value = data.value
    db.commit()
    db.refresh(setting)

    # If this is a storage config update, reload the storage service
    if key.endswith("_config"):
        from app.services.storage_service import _load_provider_config, reload_storage_service
        provider = key.rsplit("_config", 1)[0]
        try:
            new_config = _load_provider_config(provider)
            if new_config.get("bucket") or new_config.get("enabled") is False:
                reload_storage_service(provider, new_config)
        except Exception:
            pass

    return setting


@router.post("/storage/test", response_model=StorageTestResult)
async def test_storage_connection(
    body: StorageTestRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.manage")
    from app.services.storage_service import _load_provider_config, get_storage_service, reload_storage_service
    provider = body.provider
    config = _load_provider_config(provider)
    if config.get("enabled") is False:
        return StorageTestResult(success=False, message=f"请先启用 {provider}")
    if not config.get("bucket"):
        return StorageTestResult(success=False, message=f"请先配置 {provider} 的 Bucket")
    try:
        reload_storage_service(provider, config)
        storage = get_storage_service()
        result = await storage.test_connection()
        return StorageTestResult(success=result, message="Connection successful" if result else "Connection failed")
    except Exception as e:
        return StorageTestResult(success=False, message=str(e))
