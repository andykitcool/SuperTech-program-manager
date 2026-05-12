import base64
import json
import secrets
import time
from datetime import datetime
from typing import Any, Optional

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import PrintRecord, SystemSettings
from app.utils.network_settings import build_public_url


WECHAT_PAY_ENABLED_KEY = "wechat_pay_enabled"
WECHAT_PAY_APPID_KEY = "wechat_pay_appid"
WECHAT_PAY_MCHID_KEY = "wechat_pay_mchid"
WECHAT_PAY_API_V3_KEY_KEY = "wechat_pay_api_v3_key"
WECHAT_PAY_MERCHANT_SERIAL_NO_KEY = "wechat_pay_merchant_serial_no"
WECHAT_PAY_PRIVATE_KEY_KEY = "wechat_pay_private_key"
WECHAT_PAY_NOTIFY_URL_KEY = "wechat_pay_notify_url"
WECHAT_PAY_DESCRIPTION_KEY = "wechat_pay_description"

JSAPI_ENDPOINT = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"
JSAPI_SIGN_URL = "/v3/pay/transactions/jsapi"


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting and setting.value is not None else default


def _load_config(db: Session) -> dict[str, str]:
    return {
        "enabled": get_setting(db, WECHAT_PAY_ENABLED_KEY, "false"),
        "appid": get_setting(db, WECHAT_PAY_APPID_KEY, ""),
        "mchid": get_setting(db, WECHAT_PAY_MCHID_KEY, ""),
        "api_v3_key": get_setting(db, WECHAT_PAY_API_V3_KEY_KEY, ""),
        "merchant_serial_no": get_setting(db, WECHAT_PAY_MERCHANT_SERIAL_NO_KEY, ""),
        "private_key": get_setting(db, WECHAT_PAY_PRIVATE_KEY_KEY, ""),
        "notify_url": get_setting(db, WECHAT_PAY_NOTIFY_URL_KEY, "") or build_public_url(db, "/api/public/print/wechat-notify"),
        "description": get_setting(db, WECHAT_PAY_DESCRIPTION_KEY, "Photo print"),
    }


def _require_config(db: Session) -> dict[str, str]:
    config = _load_config(db)
    if config["enabled"] != "true":
        raise HTTPException(status_code=403, detail="Wechat Pay is not enabled")
    missing = [
        key
        for key in ("appid", "mchid", "api_v3_key", "merchant_serial_no", "private_key", "notify_url")
        if not str(config.get(key) or "").strip()
    ]
    if missing:
        raise HTTPException(status_code=400, detail=f"Wechat Pay config missing: {', '.join(missing)}")
    official_config = {}
    try:
        official_config = json.loads(get_setting(db, "wechat_official_account_config", "{}") or "{}")
    except Exception:
        official_config = {}
    official_appid = str(official_config.get("appid") or "").strip()
    if official_appid and official_appid != config["appid"]:
        raise HTTPException(
            status_code=400,
            detail="Wechat OAuth appid and Wechat Pay appid do not match; please update the official account config and re-authorize.",
        )
    return config


def _load_private_key(private_key_text: str):
    pem = private_key_text.strip().replace("\\n", "\n").encode("utf-8")
    try:
        return serialization.load_pem_private_key(pem, password=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Wechat Pay private key: {exc}") from exc


def _rsa_sign(message: str, private_key_text: str) -> str:
    private_key = _load_private_key(private_key_text)
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def _auth_header(config: dict[str, str], method: str, url_path: str, body: str) -> str:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = _rsa_sign(message, config["private_key"])
    return (
        'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{config["mchid"]}",'
        f'nonce_str="{nonce}",'
        f'signature="{signature}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{config["merchant_serial_no"]}"'
    )


def _jsapi_pay_params(appid: str, prepay_id: str, private_key_text: str) -> dict[str, str]:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    package = f"prepay_id={prepay_id}"
    message = f"{appid}\n{timestamp}\n{nonce}\n{package}\n"
    return {
        "appId": appid,
        "timeStamp": timestamp,
        "nonceStr": nonce,
        "package": package,
        "signType": "RSA",
        "paySign": _rsa_sign(message, private_key_text),
    }


def ensure_payment_order(record: PrintRecord) -> str:
    if record.payment_order_id:
        return record.payment_order_id
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    record.payment_order_id = f"PR{record.id}{stamp}"
    return record.payment_order_id


async def create_jsapi_payment(db: Session, record: PrintRecord, openid: str) -> dict[str, Any]:
    config = _require_config(db)
    amount = int(record.payment_amount or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")
    if not openid:
        raise HTTPException(status_code=400, detail="Wechat openid is required for JSAPI payment")

    out_trade_no = ensure_payment_order(record)
    body_data = {
        "appid": config["appid"],
        "mchid": config["mchid"],
        "description": config["description"][:127] or "Photo print",
        "out_trade_no": out_trade_no,
        "notify_url": config["notify_url"],
        "amount": {"total": amount, "currency": "CNY"},
        "payer": {"openid": openid},
    }
    body = json.dumps(body_data, ensure_ascii=False, separators=(",", ":"))
    headers = {
        "Authorization": _auth_header(config, "POST", JSAPI_SIGN_URL, body),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(JSAPI_ENDPOINT, content=body.encode("utf-8"), headers=headers)
    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json().get("message") or response.text
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Wechat Pay order failed: {detail}")

    data = response.json()
    prepay_id = data.get("prepay_id")
    if not prepay_id:
        raise HTTPException(status_code=502, detail="Wechat Pay did not return prepay_id")
    return {
        "out_trade_no": out_trade_no,
        "amount": amount,
        "pay_params": _jsapi_pay_params(config["appid"], prepay_id, config["private_key"]),
    }


def decrypt_notification(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    config = _require_config(db)
    resource = payload.get("resource") or {}
    ciphertext = resource.get("ciphertext")
    nonce = resource.get("nonce")
    associated_data = resource.get("associated_data") or ""
    if not ciphertext or not nonce:
        raise HTTPException(status_code=400, detail="Invalid Wechat Pay notification resource")

    key = config["api_v3_key"].encode("utf-8")
    if len(key) != 32:
        raise HTTPException(status_code=400, detail="Wechat Pay API v3 key must be 32 bytes")
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(
        nonce.encode("utf-8"),
        base64.b64decode(ciphertext),
        associated_data.encode("utf-8"),
    )
    return json.loads(plaintext.decode("utf-8"))
