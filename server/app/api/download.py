from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Photo, DownloadRecord

router = APIRouter()


# ============================================================
# Pydantic Schemas
# ============================================================

class DownloadRecordOut(BaseModel):
    id: int
    photo_id: Optional[int]
    photo_url: Optional[str]
    program_name: Optional[str]
    created_at: Optional[str]


class DownloadRecordListOut(BaseModel):
    items: List[DownloadRecordOut]
    total: int
    page: int
    page_size: int


# ============================================================
# 公开接口：创建下载记录
# ============================================================

class CreateDownloadRequest(BaseModel):
    photo_id: int
    openid: Optional[str] = None
    nickname: Optional[str] = None


@router.post("/records")
def create_download_record(
    data: CreateDownloadRequest,
    db: Session = Depends(get_db),
):
    """创建下载记录"""
    photo = db.query(Photo).filter(Photo.id == data.photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    from app.models import Program
    program = None
    program_name = None
    if photo.program_id:
        program = db.query(Program).filter(Program.id == photo.program_id).first()
        if program:
            program_name = program.name

    record = DownloadRecord(
        activity_id=photo.activity_id,
        program_id=photo.program_id,
        photo_id=photo.id,
        user_identifier=data.openid or "anonymous",
        user_name=data.nickname or "访客",
        photo_url=photo.storage_url or photo.wotu_url,
        program_name=program_name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"message": "download recorded", "record_id": record.id}


# ============================================================
# 公开接口：查询用户下载记录
# ============================================================

@router.get("/records", response_model=DownloadRecordListOut)
def list_user_download_records(
    openid: str = Query(..., description="微信用户openid"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """查询用户的下载记录"""
    query = db.query(DownloadRecord).filter(DownloadRecord.user_identifier == openid)
    total = query.count()
    records = (
        query.order_by(DownloadRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return DownloadRecordListOut(
        items=[
            DownloadRecordOut(
                id=r.id,
                photo_id=r.photo_id,
                photo_url=r.photo_url,
                program_name=r.program_name,
                created_at=str(r.created_at) if r.created_at else None,
            )
            for r in records
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/records/{record_id}")
def delete_user_download_record(
    record_id: int,
    openid: str = Query(..., description="微信用户openid"),
    db: Session = Depends(get_db),
):
    """删除用户自己的下载记录"""
    record = db.query(DownloadRecord).filter(DownloadRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Download record not found")

    if record.user_identifier != openid:
        raise HTTPException(status_code=403, detail="No permission to delete this record")

    db.delete(record)
    db.commit()
    return {"message": "download record deleted", "id": record_id}
