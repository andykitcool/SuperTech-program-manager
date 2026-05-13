"""Migrate local /uploads image references to configured cloud storage.

Run from the repository root:
    py -3.11 server/scripts/migrate_uploads_to_cloud.py --dry-run
    py -3.11 server/scripts/migrate_uploads_to_cloud.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
import re
import site
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


SCRIPT_PATH = Path(__file__).resolve()
SERVER_DIR = SCRIPT_PATH.parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))
USER_SITE = site.getusersitepackages()
if USER_SITE and USER_SITE not in sys.path:
    sys.path.append(USER_SITE)

import pymysql  # noqa: E402
from app.storage.aliyun import AliyunOSSAdapter  # noqa: E402
from app.storage.qiniu import QiniuAdapter  # noqa: E402
from app.storage.tencent import TencentCOSAdapter  # noqa: E402


UPLOADS_DIR = SERVER_DIR / "uploads"
UPLOAD_MARKERS = ("/uploads/", "uploads/")
PROVIDER_DEFAULTS = {
    "aliyun": {
        "access_key_id": "",
        "access_key_secret": "",
        "bucket": "",
        "endpoint": "",
        "region": "oss-cn-hangzhou",
    },
    "tencent": {
        "secret_id": "",
        "secret_key": "",
        "bucket": "",
        "region": "ap-guangzhou",
    },
    "qiniu": {
        "access_key": "",
        "secret_key": "",
        "bucket": "",
        "domain": "",
    },
}


@dataclass(frozen=True)
class UploadRef:
    value: str
    relative_path: str
    file_path: Path


def load_env_file() -> None:
    env_path = SERVER_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def connect_db():
    load_env_file()
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "supertech_pm"),
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_provider_config(conn, provider: str) -> dict:
    config = PROVIDER_DEFAULTS.get(provider, {}).copy()
    with conn.cursor() as cursor:
        cursor.execute("SELECT value FROM system_settings WHERE `key`=%s", (f"{provider}_config",))
        row = cursor.fetchone()
    if row and row.get("value"):
        config.update(json.loads(row["value"]))
    if "enabled" not in config:
        config["enabled"] = bool(config.get("bucket"))
    return config


def create_storage(conn):
    provider = None
    config = None
    for candidate in ("qiniu", "aliyun", "tencent"):
        candidate_config = load_provider_config(conn, candidate)
        if candidate_config.get("bucket") and candidate_config.get("enabled") is not False:
            provider = candidate
            config = candidate_config
            break
    if not provider:
        provider = os.getenv("DEFAULT_STORAGE_PROVIDER", "aliyun")
        config = load_provider_config(conn, provider)
    if not config or config.get("enabled") is False or not config.get("bucket"):
        return None
    adapters = {
        "aliyun": AliyunOSSAdapter,
        "qiniu": QiniuAdapter,
        "tencent": TencentCOSAdapter,
    }
    return adapters[provider](config)


def is_local_upload_value(value: str | None) -> bool:
    if not value:
        return False
    return "/uploads/" in value or value.startswith("uploads/")


def extract_upload_relative_path(value: str) -> str | None:
    parsed = urlparse(value)
    candidate = unquote(parsed.path or value)
    for marker in UPLOAD_MARKERS:
        index = candidate.find(marker)
        if index >= 0:
            return candidate[index + len(marker) :].lstrip("/\\").replace("\\", "/")
    return None


def build_upload_ref(value: str) -> UploadRef | None:
    relative_path = extract_upload_relative_path(value)
    if not relative_path:
        return None
    file_path = (UPLOADS_DIR / relative_path).resolve()
    try:
        file_path.relative_to(UPLOADS_DIR.resolve())
    except ValueError:
        return None
    return UploadRef(value=value, relative_path=relative_path, file_path=file_path)


def iter_local_upload_refs(text: str | None) -> Iterable[UploadRef]:
    if not text or "uploads/" not in text:
        return []

    refs: list[UploadRef] = []
    normalized = text.replace("\\/", "/")
    matches = re.findall(
        r"(?:https?://[^\"'\s,)]+)?/?uploads/[^\"'\s,)\\}\]]+",
        normalized,
    )
    for value in matches:
        ref = build_upload_ref(value)
        if ref:
            refs.append(ref)
    return refs


def collect_database_refs(conn) -> dict[str, UploadRef]:
    refs: dict[str, UploadRef] = {}

    def add_value(value: str | None):
        if not is_local_upload_value(value):
            return
        ref = build_upload_ref(value)
        if ref:
            refs.setdefault(value, ref)

    with conn.cursor() as cursor:
        cursor.execute("SELECT storage_url, thumbnail_url FROM decoration_materials")
        for item in cursor.fetchall():
            add_value(item.get("storage_url"))
            add_value(item.get("thumbnail_url"))

        cursor.execute("SELECT cover_image FROM activities")
        for item in cursor.fetchall():
            add_value(item.get("cover_image"))

        cursor.execute("SELECT storage_url FROM photos")
        for item in cursor.fetchall():
            add_value(item.get("storage_url"))

        cursor.execute("SELECT print_image_url, print_payload_json FROM print_records")
        for item in cursor.fetchall():
            add_value(item.get("print_image_url"))
            for ref in iter_local_upload_refs(item.get("print_payload_json")):
                refs.setdefault(ref.value, ref)

        cursor.execute("SELECT value FROM system_settings")
        for item in cursor.fetchall():
            for ref in iter_local_upload_refs(item.get("value")):
                refs.setdefault(ref.value, ref)

    return refs


async def upload_ref(ref: UploadRef, storage) -> str:
    content_type, _ = mimetypes.guess_type(ref.file_path.name)
    data = ref.file_path.read_bytes()
    return await storage.upload_file(data, ref.relative_path, content_type=content_type)


def replace_text(value: str | None, mapping: dict[str, str]) -> str | None:
    if not value:
        return value
    updated = value
    for old, new in mapping.items():
        updated = updated.replace(old, new)
        updated = updated.replace(old.replace("/", "\\/"), new.replace("/", "\\/"))
    return updated


def apply_database_updates(conn, mapping: dict[str, str]) -> int:
    changed = 0

    def update_table(table: str, id_field: str, fields: tuple[str, ...]):
        nonlocal changed
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT {id_field}, {', '.join(fields)} FROM {table}")
            for row in cursor.fetchall():
                updates = {}
                for field in fields:
                    old = row.get(field)
                    new = replace_text(old, mapping)
                    if new != old:
                        updates[field] = new
                if not updates:
                    continue
                set_clause = ", ".join(f"{field}=%s" for field in updates)
                params = list(updates.values()) + [row[id_field]]
                cursor.execute(f"UPDATE {table} SET {set_clause} WHERE {id_field}=%s", params)
                changed += len(updates)

    update_table("decoration_materials", "id", ("storage_url", "thumbnail_url"))
    update_table("activities", "id", ("cover_image",))
    update_table("photos", "id", ("storage_url",))
    update_table("print_records", "id", ("print_image_url", "print_payload_json"))
    update_table("system_settings", "id", ("value",))
    return changed


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only report what would change.")
    args = parser.parse_args()

    conn = connect_db()
    try:
        storage = create_storage(conn)
        if not storage:
            print("Cloud storage is not configured. Configure qiniu/aliyun/tencent first.")
            return 2

        refs = collect_database_refs(conn)
        existing_refs = {old: ref for old, ref in refs.items() if ref.file_path.exists()}
        missing_refs = {old: ref for old, ref in refs.items() if not ref.file_path.exists()}

        print(f"Found {len(refs)} local upload URL references in database.")
        print(f"Found {len(existing_refs)} files ready to upload.")
        if missing_refs:
            print(f"Skipped {len(missing_refs)} references because local files are missing.")

        if args.dry_run:
            for old, ref in list(existing_refs.items())[:20]:
                print(f"DRY-RUN {old} -> {ref.relative_path}")
            if len(existing_refs) > 20:
                print(f"... {len(existing_refs) - 20} more")
            return 0

        mapping: dict[str, str] = {}
        for index, (old, ref) in enumerate(existing_refs.items(), start=1):
            new_url = await upload_ref(ref, storage)
            mapping[old] = new_url
            print(f"[{index}/{len(existing_refs)}] {old} -> {new_url}")

        changed = apply_database_updates(conn, mapping)
        conn.commit()
        print(f"Updated {changed} database fields/text blobs.")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
