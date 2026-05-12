import json
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models import SystemSettings


NETWORK_SETTINGS_KEY = "network_settings"
SSL_DIR = Path("/app/uploads/network/ssl")
NGINX_DIR = Path("/app/uploads/network/nginx")
SSL_CERT_PATH = SSL_DIR / "site_cert.pem"
SSL_KEY_PATH = SSL_DIR / "site_key.pem"
NGINX_SSL_CONF_PATH = NGINX_DIR / "ssl.conf"


DEFAULT_NETWORK_SETTINGS = {
    "domain": "",
    "base_url": "",
    "ssl_enabled": False,
    "force_https": True,
}


def _get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting and setting.value is not None else default


def _set_setting(db: Session, key: str, value: str, description: str = "") -> None:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        db.add(SystemSettings(key=key, value=value, description=description))
    else:
        setting.value = value
        if description:
            setting.description = description


def normalize_base_url(domain: str = "", base_url: str = "", ssl_enabled: bool = False) -> str:
    text = (base_url or domain or "").strip()
    if not text:
        return ""
    text = text.rstrip("/")
    if ssl_enabled and text.startswith("http://"):
        return "https://" + text[len("http://"):]
    if text.startswith("http://") or text.startswith("https://"):
        return text
    scheme = "https" if ssl_enabled else "http"
    return f"{scheme}://{text}"


def load_network_settings(db: Session) -> dict:
    raw = _get_setting(db, NETWORK_SETTINGS_KEY, "")
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    result = {**DEFAULT_NETWORK_SETTINGS, **data}
    result["base_url"] = normalize_base_url(
        str(result.get("domain") or ""),
        str(result.get("base_url") or ""),
        bool(result.get("ssl_enabled")),
    )
    result["has_ssl_cert"] = SSL_CERT_PATH.exists()
    result["has_ssl_key"] = SSL_KEY_PATH.exists()
    result["wechat_pay_notify_url"] = build_public_url(db, "/api/public/print/wechat-notify")
    result["wechat_pay_refund_notify_url"] = build_public_url(db, "/api/public/print/wechat-refund-notify")
    return result


def save_network_settings(db: Session, data: dict) -> dict:
    current = load_network_settings(db)
    merged = {**current, **data}
    ssl_enabled = bool(merged.get("ssl_enabled"))
    domain = str(merged.get("domain") or "").strip()
    base_url = normalize_base_url(domain, str(merged.get("base_url") or ""), ssl_enabled)
    payload = {
        "domain": domain,
        "base_url": base_url,
        "ssl_enabled": ssl_enabled,
        "force_https": bool(merged.get("force_https", True)),
    }
    _set_setting(
        db,
        NETWORK_SETTINGS_KEY,
        json.dumps(payload, ensure_ascii=False),
        "Network domain, base URL and SSL settings",
    )
    db.commit()
    return load_network_settings(db)


def save_ssl_files(cert_pem: Optional[str], key_pem: Optional[str]) -> dict:
    SSL_DIR.mkdir(parents=True, exist_ok=True)
    if cert_pem:
        SSL_CERT_PATH.write_text(cert_pem.strip() + "\n", encoding="utf-8")
    if key_pem:
        SSL_KEY_PATH.write_text(key_pem.strip() + "\n", encoding="utf-8")
    return {"has_ssl_cert": SSL_CERT_PATH.exists(), "has_ssl_key": SSL_KEY_PATH.exists()}


def build_public_url(db: Session, path: str) -> str:
    raw = _get_setting(db, NETWORK_SETTINGS_KEY, "")
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    base_url = normalize_base_url(
        str((data or {}).get("domain") or ""),
        str((data or {}).get("base_url") or ""),
        bool((data or {}).get("ssl_enabled")),
    )
    if not base_url:
        return ""
    return f"{base_url}/{path.lstrip('/')}"


def write_nginx_ssl_config(settings: dict) -> None:
    domain = str(settings.get("domain") or "").strip()
    if not domain or not settings.get("ssl_enabled"):
        if NGINX_SSL_CONF_PATH.exists():
            NGINX_SSL_CONF_PATH.unlink()
        return

    NGINX_DIR.mkdir(parents=True, exist_ok=True)
    conf = f"""
server {{
    listen 443 ssl;
    server_name {domain};

    ssl_certificate /etc/nginx/ssl/site_cert.pem;
    ssl_certificate_key /etc/nginx/ssl/site_key.pem;

    root /usr/share/nginx/html;
    index index.html;

    location / {{
        try_files $uri $uri/ /index.html;
    }}

    location /api/ {{
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        client_max_body_size 5G;
        proxy_read_timeout 600s;
    }}

    location /uploads/ {{
        proxy_pass http://api:8000/uploads/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        client_max_body_size 20M;
        proxy_read_timeout 120s;
    }}
}}
""".lstrip()
    NGINX_SSL_CONF_PATH.write_text(conf, encoding="utf-8")
