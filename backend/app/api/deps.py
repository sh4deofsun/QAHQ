from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..core.permissions import Perm
from ..core.security import decode_token
from ..db import models
from ..db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    username = decode_token(token)
    if username:
        user = db.query(models.User).filter_by(username=username).first()
        if user and user.is_active:
            return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require(perm: Perm):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if perm.value not in user.permissions:
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm.value}")
        return user

    return checker
