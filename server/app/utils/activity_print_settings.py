import json
from typing import Any, Mapping, Optional

from sqlalchemy.orm import Session

from app.models import SystemSettings

PRINT_FREE_QUOTA_KEY = "print_free_quota"
PRINT_PRICE_KEY = "print_price"
PRINT_RENDER_MODE_KEY = "print_render_mode"
PRINT_RENDER_MULTIPLIER_KEY = "print_render_multiplier"
PRINT_DISPATCH_MODE_KEY = "print_dispatch_mode"
PRINT_RENDER_MODE_FRONTEND = "frontend"
PRINT_RENDER_MODE_SERVER = "server"
PRINT_DISPATCH_MODE_LANKUO = "lankuo"
PRINT_DISPATCH_MODE_LOCAL_CLIENT = "local_client"
DEFAULT_FREE_QUOTA = 2
DEFAULT_PRINT_PRICE = 100
DEFAULT_PRINT_RENDER_MULTIPLIER = 1


def activity_print_settings_key(activity_id: int) -> str:
    return f"activity_{activity_id}_print_settings"


def _get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting and setting.value is not None else default


def _set_setting(db: Session, key: str, value: str, description: str = "") -> SystemSettings:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        setting = SystemSettings(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description:
            setting.description = description
    return setting


def _to_int(value: Any, default: int, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None:
        parsed = max(parsed, min_value)
    if max_value is not None:
        parsed = min(parsed, max_value)
    return parsed


def _normalize_render_mode(value: Any) -> str:
    text = str(value or PRINT_RENDER_MODE_FRONTEND).strip()
    return text if text in {PRINT_RENDER_MODE_FRONTEND, PRINT_RENDER_MODE_SERVER} else PRINT_RENDER_MODE_FRONTEND


def _normalize_dispatch_mode(value: Any) -> str:
    text = str(value or PRINT_DISPATCH_MODE_LANKUO).strip()
    allowed = {PRINT_DISPATCH_MODE_LANKUO, PRINT_DISPATCH_MODE_LOCAL_CLIENT, "disabled"}
    return text if text in allowed else PRINT_DISPATCH_MODE_LANKUO


def _load_global_defaults(db: Session) -> dict:
    return {
        "print_free_quota": _to_int(_get_setting(db, PRINT_FREE_QUOTA_KEY, DEFAULT_FREE_QUOTA), DEFAULT_FREE_QUOTA, 0),
        "print_price": _to_int(_get_setting(db, PRINT_PRICE_KEY, DEFAULT_PRINT_PRICE), DEFAULT_PRINT_PRICE, 0),
        "print_render_mode": _normalize_render_mode(_get_setting(db, PRINT_RENDER_MODE_KEY, PRINT_RENDER_MODE_FRONTEND)),
        "print_render_multiplier": _to_int(
            _get_setting(db, PRINT_RENDER_MULTIPLIER_KEY, DEFAULT_PRINT_RENDER_MULTIPLIER),
            DEFAULT_PRINT_RENDER_MULTIPLIER,
            1,
            3,
        ),
        "print_dispatch_mode": _normalize_dispatch_mode(_get_setting(db, PRINT_DISPATCH_MODE_KEY, PRINT_DISPATCH_MODE_LANKUO)),
    }


def get_activity_print_settings(db: Session, activity_id: int) -> dict:
    settings = _load_global_defaults(db)
    raw = _get_setting(db, activity_print_settings_key(activity_id), "")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                settings.update(parsed)
        except Exception:
            pass

    settings["print_free_quota"] = _to_int(settings.get("print_free_quota"), DEFAULT_FREE_QUOTA, 0)
    settings["print_price"] = _to_int(settings.get("print_price"), DEFAULT_PRINT_PRICE, 0)
    settings["print_render_mode"] = _normalize_render_mode(settings.get("print_render_mode"))
    settings["print_render_multiplier"] = _to_int(
        settings.get("print_render_multiplier"),
        DEFAULT_PRINT_RENDER_MULTIPLIER,
        1,
        3,
    )
    settings["print_dispatch_mode"] = _normalize_dispatch_mode(settings.get("print_dispatch_mode"))
    return settings


def update_activity_print_settings(db: Session, activity_id: int, data: Mapping[str, Any]) -> dict:
    settings = get_activity_print_settings(db, activity_id)
    if data.get("print_free_quota") is not None:
        settings["print_free_quota"] = _to_int(data.get("print_free_quota"), DEFAULT_FREE_QUOTA, 0)
    if data.get("print_price") is not None:
        settings["print_price"] = _to_int(data.get("print_price"), DEFAULT_PRINT_PRICE, 0)
    if data.get("print_render_mode") is not None:
        settings["print_render_mode"] = _normalize_render_mode(data.get("print_render_mode"))
    if data.get("print_render_multiplier") is not None:
        settings["print_render_multiplier"] = _to_int(data.get("print_render_multiplier"), DEFAULT_PRINT_RENDER_MULTIPLIER, 1, 3)
    if data.get("print_dispatch_mode") is not None:
        settings["print_dispatch_mode"] = _normalize_dispatch_mode(data.get("print_dispatch_mode"))

    _set_setting(
        db,
        activity_print_settings_key(activity_id),
        json.dumps(settings, ensure_ascii=False),
        "活动级打印设置",
    )
    db.commit()
    return settings
