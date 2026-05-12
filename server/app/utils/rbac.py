import json
from typing import Iterable, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Activity, AppUser, Role


PERMISSIONS = {
    "system.manage": "系统设置",
    "user.manage": "用户管理",
    "role.manage": "角色管理",
    "activity.manage": "活动管理",
    "program.manage": "节目管理",
    "photo.manage": "照片管理",
    "material.manage": "素材管理",
    "print.manage": "打印管理",
    "music.manage": "曲库管理",
    "sync.manage": "同步管理",
}

PRINT_ADMIN_PERMISSIONS = [
    "activity.manage",
    "material.manage",
    "print.manage",
]

DEFAULT_ROLES = [
    {
        "name": "超级管理员",
        "code": "super_admin",
        "description": "拥有系统全部权限",
        "permissions": list(PERMISSIONS.keys()),
    },
    {
        "name": "打印管理员",
        "code": "print_admin",
        "description": "浏览所有活动并管理素材、打印配置与打印订单",
        "permissions": PRINT_ADMIN_PERMISSIONS,
    },
    {
        "name": "活动管理员",
        "code": "activity_admin",
        "description": "管理被授权活动的节目、照片和常规活动资料",
        "permissions": ["activity.manage", "program.manage", "photo.manage"],
    },
]


def permissions_to_json(permissions: Iterable[str]) -> str:
    return json.dumps(sorted(set(permissions)), ensure_ascii=False)


def parse_permissions(value: Optional[str]) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
        return [item for item in data if isinstance(item, str)]
    except Exception:
        return []


def seed_default_roles(db: Session) -> None:
    for item in DEFAULT_ROLES:
        role = db.query(Role).filter(Role.code == item["code"]).first()
        if not role:
            role = Role(
                name=item["name"],
                code=item["code"],
                description=item["description"],
                permissions_json=permissions_to_json(item["permissions"]),
                is_system=True,
            )
            db.add(role)
        else:
            role.name = item["name"]
            role.description = item["description"]
            role.is_system = True
            if role.code == "print_admin":
                role.permissions_json = permissions_to_json(item["permissions"])
            elif not role.permissions_json:
                role.permissions_json = permissions_to_json(item["permissions"])
    db.commit()


def upsert_app_user_from_profile(db: Session, profile, last_seen_at=None) -> AppUser:
    user = db.query(AppUser).filter(AppUser.openid == profile.openid).first()
    if not user:
        user = AppUser(openid=profile.openid, source="wechat")
        db.add(user)
    user.source = user.source or "wechat"
    user.unionid = profile.unionid or user.unionid
    user.nickname = profile.nickname or user.nickname
    user.avatar_url = profile.avatar_url or user.avatar_url
    user.province = profile.province or user.province
    user.city = profile.city or user.city
    user.country = profile.country or user.country
    user.last_seen_at = last_seen_at or user.last_seen_at
    user.is_deleted = False
    db.flush()
    return user


def user_permissions(db: Session, openid: str) -> tuple[set[str], set[int], list[str]]:
    user = db.query(AppUser).filter(AppUser.openid == openid, AppUser.is_deleted.is_(False)).first()
    if not user or user.is_blacklisted:
        return set(), set(), []

    permissions: set[str] = set()
    activity_ids: set[int] = set()
    role_codes: list[str] = []
    for assignment in user.assignments:
        role = assignment.role
        if not role:
            continue
        role_codes.append(role.code)
        role_permissions = parse_permissions(role.permissions_json)
        permissions.update(role_permissions)
        if assignment.activity_id is not None and "activity.manage" in role_permissions:
            activity_ids.add(assignment.activity_id)

    return permissions, activity_ids, sorted(set(role_codes))


def is_super_admin(current_user: dict) -> bool:
    return current_user.get("sub") == "admin" or "super_admin" in (current_user.get("role_codes") or [])


def can_manage_all_activities(current_user: dict) -> bool:
    role_codes = current_user.get("role_codes") or []
    permissions = set(current_user.get("permissions") or [])
    return is_super_admin(current_user) or (
        "print_admin" in role_codes
        and {"activity.manage", "print.manage"}.issubset(permissions)
    )


def require_permission(current_user: dict, permission: str) -> None:
    if is_super_admin(current_user):
        return
    if permission not in (current_user.get("permissions") or []):
        raise HTTPException(status_code=403, detail="没有权限执行此操作")


def allowed_activity_ids(current_user: dict) -> Optional[set[int]]:
    if can_manage_all_activities(current_user):
        return None
    return set(current_user.get("activity_ids") or [])


def require_activity_access(db: Session, current_user: dict, activity_id: int, permission: str = "activity.manage") -> Activity:
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    if can_manage_all_activities(current_user):
        return activity
    require_permission(current_user, permission)
    ids = allowed_activity_ids(current_user)
    if ids is not None and activity_id not in ids:
        raise HTTPException(status_code=403, detail="没有此活动的管理权限")
    return activity
