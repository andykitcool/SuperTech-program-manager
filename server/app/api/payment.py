from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PrintRecord, SystemSettings
from app.utils.activity_print_settings import get_activity_print_settings
from app.utils.wechat_pay import create_jsapi_payment, decrypt_notification, get_setting

router = APIRouter(prefix="/public/print", tags=["print payment"])


WECHAT_PAY_ENABLED_KEY = "wechat_pay_enabled"
DEFAULT_FREE_QUOTA = 2
DEFAULT_PRINT_PRICE = 100


class QuotaCheckOut(BaseModel):
    free_quota: int
    used_count: int
    remaining: int
    price: int
    pay_enabled: bool


class CreatePaymentRequest(BaseModel):
    record_id: int
    openid: str


def _payment_enabled(db: Session) -> bool:
    return get_setting(db, WECHAT_PAY_ENABLED_KEY, "false") == "true"


def _mark_paid_and_dispatch(db: Session, record: PrintRecord, paid_at: datetime | None = None) -> None:
    record.payment_status = "paid"
    record.paid_at = paid_at or datetime.now()
    record.error_msg = None
    if record.status not in {"queued", "printing", "claimed", "success"}:
        record.status = "queued"
    db.commit()

    from app.utils.lankuo_client import get_effective_lankuo_config
    from app.utils.print_dispatcher import dispatch_print_task, should_dispatch_lankuo

    lankuo_cfg = get_effective_lankuo_config(db, record.activity_id)
    if record.status == "queued" and should_dispatch_lankuo(db, lankuo_cfg, record.activity_id):
        dispatch_print_task(record.id, lankuo_cfg, db)


@router.get("/quota", response_model=QuotaCheckOut)
def check_print_quota(
    activity_id: int,
    openid: str = Query(..., description="Wechat openid"),
    db: Session = Depends(get_db),
):
    activity_settings = get_activity_print_settings(db, activity_id)
    free_quota = int(activity_settings.get("print_free_quota", DEFAULT_FREE_QUOTA))
    print_price = int(activity_settings.get("print_price", DEFAULT_PRINT_PRICE))

    used_count = db.query(PrintRecord).filter(
        PrintRecord.activity_id == activity_id,
        PrintRecord.user_identifier == openid,
        PrintRecord.payment_status.in_(["free", "paid"]),
    ).count()

    return QuotaCheckOut(
        free_quota=free_quota,
        used_count=used_count,
        remaining=max(0, free_quota - used_count),
        price=print_price,
        pay_enabled=_payment_enabled(db),
    )


@router.post("/create-payment")
async def create_payment(
    data: CreatePaymentRequest,
    db: Session = Depends(get_db),
):
    record = db.query(PrintRecord).filter(PrintRecord.id == data.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Print record not found")
    if record.payment_status == "paid":
        return {"payment_status": "paid", "record_id": record.id}
    if record.payment_status == "free":
        return {"payment_status": "free", "record_id": record.id}
    if record.payment_status != "pending":
        raise HTTPException(status_code=400, detail=f"Invalid payment status: {record.payment_status}")

    pay_data = await create_jsapi_payment(db, record, data.openid)
    db.commit()
    return {
        "payment_status": "pending",
        "record_id": record.id,
        **pay_data,
    }


@router.post("/wechat-notify")
async def wechat_payment_notify(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    transaction = decrypt_notification(db, payload)
    out_trade_no = transaction.get("out_trade_no")
    if not out_trade_no:
        raise HTTPException(status_code=400, detail="Missing out_trade_no")

    record = db.query(PrintRecord).filter(PrintRecord.payment_order_id == out_trade_no).first()
    if not record:
        return {"code": "SUCCESS", "message": "ignored"}

    if transaction.get("trade_state") == "SUCCESS":
        success_time = transaction.get("success_time")
        paid_at = None
        if success_time:
            try:
                paid_at = datetime.fromisoformat(success_time.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                paid_at = datetime.now()
        _mark_paid_and_dispatch(db, record, paid_at)
    elif record.payment_status == "pending":
        record.error_msg = str(transaction.get("trade_state_desc") or transaction.get("trade_state") or "")[:500]
        db.commit()

    return {"code": "SUCCESS", "message": "success"}
