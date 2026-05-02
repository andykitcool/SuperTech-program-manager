from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Program, Photo
from app.schemas.photo import PhotoListOut
from app.schemas.activity import ProgramPublicOut
from app.utils.auth import decode_token
from jose import JWTError

router = APIRouter()
security = HTTPBearer(auto_error=False)


def _check_admin_token(credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
    """Return True if a valid admin token is provided."""
    if not credentials:
        return False
    try:
        decode_token(credentials.credentials)
        return True
    except (JWTError, Exception):
        return False


def _get_program_by_token_or_404(token: str, db: Session, is_admin: bool) -> Program:
    program = db.query(Program).filter(Program.access_token == token).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    if not is_admin and program.ready_status.value != "ready":
        raise HTTPException(status_code=404, detail="Program not found or not ready")
    return program


@router.get("/programs/{token}", response_model=ProgramPublicOut)
def public_get_program(
    token: str,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    is_admin = _check_admin_token(credentials)
    return _get_program_by_token_or_404(token, db, is_admin)


@router.get("/programs/{token}/photos", response_model=List[PhotoListOut])
def public_list_photos(
    token: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    is_admin = _check_admin_token(credentials)
    program = _get_program_by_token_or_404(token, db, is_admin)

    photos = (
        db.query(Photo)
        .filter(Photo.program_id == program.id)
        .order_by(Photo.shoot_time)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return photos
