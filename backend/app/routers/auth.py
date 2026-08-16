from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import (
    verify_password,
    create_access_token,
    get_current_payload,
    ROLE_VIEWER,
    ROLE_JUDGE,
    ROLE_ADMIN,
)
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/viewer/signup", response_model=schemas.TokenResponse)
def viewer_signup(payload: schemas.ViewerSignup, db: Session = Depends(get_db)):
    """No password. Signing up with an email is all a spectator needs to
    view results; signing up again with the same email just logs them
    back in."""
    viewer = crud.get_or_create_viewer(db, payload.email, payload.name)
    token = create_access_token(viewer.id, ROLE_VIEWER, viewer.email)
    return schemas.TokenResponse(
        access_token=token,
        role=ROLE_VIEWER,
        profile=schemas.ViewerOut.model_validate(viewer).model_dump(),
    )


@router.post("/judge/login", response_model=schemas.TokenResponse)
def judge_login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    judge = crud.get_judge_by_username(db, payload.username)
    if not judge or not verify_password(payload.password, judge.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    token = create_access_token(judge.id, ROLE_JUDGE, judge.username)
    return schemas.TokenResponse(
        access_token=token,
        role=ROLE_JUDGE,
        profile=schemas.JudgeOut.model_validate(judge).model_dump(),
    )


@router.post("/admin/login", response_model=schemas.TokenResponse)
def admin_login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    admin = crud.get_admin_by_username(db, payload.username)
    if not admin or not verify_password(payload.password, admin.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    token = create_access_token(admin.id, ROLE_ADMIN, admin.username)
    return schemas.TokenResponse(
        access_token=token,
        role=ROLE_ADMIN,
        profile=schemas.AdminOut.model_validate(admin).model_dump(),
    )


@router.get("/me", response_model=schemas.MeOut)
def me(payload: dict = Depends(get_current_payload), db: Session = Depends(get_db)):
    """Used on app load to re-validate whatever session is stored
    locally and fetch fresh profile info, regardless of role."""
    role = payload["role"]
    if role == ROLE_JUDGE:
        judge = crud.get_judge(db, payload["id"])
        if not judge:
            raise HTTPException(401, "Judge account no longer exists.")
        return schemas.MeOut(role=role, profile=schemas.JudgeOut.model_validate(judge).model_dump())
    if role == ROLE_ADMIN:
        admin = db.query(crud.models.Admin).filter(crud.models.Admin.id == payload["id"]).first()
        if not admin:
            raise HTTPException(401, "Admin account no longer exists.")
        return schemas.MeOut(role=role, profile=schemas.AdminOut.model_validate(admin).model_dump())
    if role == ROLE_VIEWER:
        viewer = db.query(crud.models.Viewer).filter(crud.models.Viewer.id == payload["id"]).first()
        if not viewer:
            raise HTTPException(401, "Viewer account no longer exists.")
        return schemas.MeOut(role=role, profile=schemas.ViewerOut.model_validate(viewer).model_dump())
    raise HTTPException(401, "Unknown session type.")
