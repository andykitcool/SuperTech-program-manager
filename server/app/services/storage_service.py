import json
import threading
from typing import Optional

from app.storage import BaseStorageAdapter
from app.storage.aliyun import AliyunOSSAdapter
from app.storage.tencent import TencentCOSAdapter
from app.storage.qiniu import QiniuAdapter


# Singleton storage service
_storage_instance: Optional[BaseStorageAdapter] = None
_storage_lock = threading.Lock()
_current_provider: Optional[str] = None


def _detect_configured_provider() -> Optional[str]:
    """Detect which provider has been configured in the database."""
    for provider in ["qiniu", "aliyun", "tencent"]:
        config = _load_provider_config(provider)
        if config.get("bucket") and config.get("enabled") is not False:
            return provider
    return None


def _load_provider_config(provider: str) -> dict:
    """Load provider config from database, fall back to hardcoded defaults."""
    env_defaults = {
        "aliyun": {
            "access_key_id": "", "access_key_secret": "",
            "bucket": "", "endpoint": "", "region": "oss-cn-hangzhou",
        },
        "tencent": {
            "secret_id": "", "secret_key": "",
            "bucket": "", "region": "ap-guangzhou",
        },
        "qiniu": {
            "access_key": "", "secret_key": "",
            "bucket": "", "domain": "",
        },
    }

    try:
        from app.database import SessionLocal
        from app.models import SystemSettings
        db = SessionLocal()
        try:
            setting = db.query(SystemSettings).filter(
                SystemSettings.key == f"{provider}_config"
            ).first()
            if setting and setting.value:
                db_config = json.loads(setting.value)
                merged = {**env_defaults.get(provider, {}), **db_config}
                if "enabled" not in db_config:
                    merged["enabled"] = bool(merged.get("bucket"))
                return merged
        finally:
            db.close()
    except Exception:
        pass

    return env_defaults.get(provider, {})


def _create_adapter(provider: str) -> BaseStorageAdapter:
    config = _load_provider_config(provider)
    if config.get("enabled") is False:
        raise ValueError(f"Storage provider '{provider}' is disabled")
    if not config.get("bucket"):
        raise ValueError(f"Storage provider '{provider}' is not configured")

    adapters = {
        "aliyun": AliyunOSSAdapter,
        "tencent": TencentCOSAdapter,
        "qiniu": QiniuAdapter,
    }
    adapter_cls = adapters.get(provider)
    if not adapter_cls:
        raise ValueError(f"Unknown storage provider: {provider}")
    return adapter_cls(config)


def get_storage_service() -> BaseStorageAdapter:
    """Get the current storage service instance (singleton)."""
    global _storage_instance, _current_provider

    with _storage_lock:
        if _storage_instance is not None:
            return _storage_instance

        # Detect configured provider from database
        provider = _detect_configured_provider() or _current_provider
        if not provider:
            from app.config import get_settings
            provider = get_settings().DEFAULT_STORAGE_PROVIDER
        config = _load_provider_config(provider)
        if config.get("bucket"):
            _storage_instance = _create_adapter(provider)
            _current_provider = provider
        return _storage_instance


def get_video_thumbnail_url(video_url: str) -> Optional[str]:
    """Get video thumbnail URL based on current storage provider."""
    if not video_url:
        return None
    try:
        storage = get_storage_service()
        if storage:
            return storage.get_video_thumbnail_url(video_url)
    except Exception:
        pass
    return None


def get_upload_token(key: str, expires: int = 3600) -> str:
    """Generate an upload token for client-side direct upload."""
    storage = get_storage_service()
    if storage:
        return storage.generate_upload_token(key, expires)
    raise ValueError("No storage service available")


def reload_storage_service(provider: str, config: dict):
    """Force reload storage service with new provider/config."""
    global _storage_instance, _current_provider
    with _storage_lock:
        if config.get("enabled") is False or not config.get("bucket"):
            if _current_provider == provider:
                _storage_instance = None
                _current_provider = None
            return

        adapters = {
            "aliyun": AliyunOSSAdapter,
            "tencent": TencentCOSAdapter,
            "qiniu": QiniuAdapter,
        }
        adapter_cls = adapters.get(provider)
        if adapter_cls:
            _storage_instance = adapter_cls(config)
            _current_provider = provider
