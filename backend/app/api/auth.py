from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..core.security import create_access_token, verify_password
from ..db import models
from ..db.session import get_db
from ..services.ldap import verify_ldap_credentials
from .deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def authenticate(db: Session, username: str, password: str) -> models.User | None:
    user = db.query(models.User).filter_by(username=username).first()

    if user and user.auth_source == "local":
        if user.hashed_password and verify_password(password, user.hashed_password):
            return user
        return None  # local user: never fall through to LDAP

    if verify_ldap_credentials(username, password):
        if not user:
            from ..core.config import settings

            default_role = db.query(models.Role).filter_by(name=settings.ldap_default_role).first()
            user = models.User(
                username=username,
                auth_source="ldap",
                roles=[default_role] if default_role else [],
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    return None


@router.post("/token")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = authenticate(db, form_data.username, form_data.password)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user.username), "token_type": "bearer"}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return {
        "username": user.username,
        "auth_source": user.auth_source,
        "roles": [r.name for r in user.roles],
        "permissions": sorted(user.permissions),
    }
