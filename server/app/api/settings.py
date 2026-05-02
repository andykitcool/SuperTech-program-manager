import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.utils.auth import get_current_user
from app.models import SystemSettings
from app.schemas.settings import SettingsOut, SettingsUpdate, StorageTestResult, StorageTestRequest

router = APIRouter()


@router.get("", response_model=List[SettingsOut])
def list_settings(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return db.query(SystemSettings).all()


@router.get("/{key}")
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        return {"id": 0, "key": key, "value": None, "description": None, "created_at": None, "updated_at": None}
    return setting


@router.put("/{key}", response_model=SettingsOut)
def update_setting(
    key: str,
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
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
    _user: dict = Depends(get_current_user),
):
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
