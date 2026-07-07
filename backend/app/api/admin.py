from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.permissions import Perm
from ..core.security import hash_password
from ..db import models
from ..db.session import get_db
from .deps import require

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---- Users ----

class UserCreate(BaseModel):
    username: str
    password: str
    roles: list[str] = []


class UserUpdate(BaseModel):
    password: str | None = None
    is_active: bool | None = None
    roles: list[str] | None = None


def _roles_by_name(db: Session, names: list[str]) -> list[models.Role]:
    roles = db.query(models.Role).filter(models.Role.name.in_(names)).all()
    if len(roles) != len(set(names)):
        raise HTTPException(status_code=400, detail="Unknown role name")
    return roles


def serialize_user(u: models.User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "auth_source": u.auth_source,
        "is_active": u.is_active,
        "roles": [r.name for r in u.roles],
        "created_at": u.created_at,
    }


@router.get("/users", dependencies=[Depends(require(Perm.USER_MANAGE))])
def list_users(db: Session = Depends(get_db)):
    return [serialize_user(u) for u in db.query(models.User).order_by(models.User.username)]


@router.post("/users", dependencies=[Depends(require(Perm.USER_MANAGE))], status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter_by(username=body.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = models.User(
        username=body.username,
        hashed_password=hash_password(body.password),
        auth_source="local",
        roles=_roles_by_name(db, body.roles),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.patch("/users/{user_id}", dependencies=[Depends(require(Perm.USER_MANAGE))])
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.password is not None:
        if user.auth_source != "local":
            raise HTTPException(status_code=400, detail="Cannot set password for LDAP users")
        user.hashed_password = hash_password(body.password)
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.roles is not None:
        user.roles = _roles_by_name(db, body.roles)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.delete("/users/{user_id}", dependencies=[Depends(require(Perm.USER_MANAGE))], status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()


# ---- Roles ----

class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    description: str | None = None
    permissions: list[str] | None = None


def _perms_by_code(db: Session, codes: list[str]) -> list[models.Permission]:
    valid = {p.value for p in Perm}
    if not set(codes) <= valid:
        raise HTTPException(status_code=400, detail="Unknown permission code")
    return db.query(models.Permission).filter(models.Permission.code.in_(codes)).all()


def serialize_role(r: models.Role) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "permissions": sorted(p.code for p in r.permissions),
    }


@router.get("/roles", dependencies=[Depends(require(Perm.ROLE_MANAGE))])
def list_roles(db: Session = Depends(get_db)):
    return [serialize_role(r) for r in db.query(models.Role).order_by(models.Role.name)]


@router.get("/permissions", dependencies=[Depends(require(Perm.ROLE_MANAGE))])
def list_permissions():
    return [p.value for p in Perm]


@router.post("/roles", dependencies=[Depends(require(Perm.ROLE_MANAGE))], status_code=201)
def create_role(body: RoleCreate, db: Session = Depends(get_db)):
    if db.query(models.Role).filter_by(name=body.name).first():
        raise HTTPException(status_code=409, detail="Role already exists")
    role = models.Role(
        name=body.name,
        description=body.description,
        permissions=_perms_by_code(db, body.permissions),
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return serialize_role(role)


@router.patch("/roles/{role_id}", dependencies=[Depends(require(Perm.ROLE_MANAGE))])
def update_role(role_id: int, body: RoleUpdate, db: Session = Depends(get_db)):
    role = db.get(models.Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name == "admin":
        raise HTTPException(status_code=400, detail="The admin role cannot be modified")
    if body.description is not None:
        role.description = body.description
    if body.permissions is not None:
        role.permissions = _perms_by_code(db, body.permissions)
    db.commit()
    db.refresh(role)
    return serialize_role(role)


@router.delete("/roles/{role_id}", dependencies=[Depends(require(Perm.ROLE_MANAGE))], status_code=204)
def delete_role(role_id: int, db: Session = Depends(get_db)):
    role = db.get(models.Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name == "admin":
        raise HTTPException(status_code=400, detail="The admin role cannot be deleted")
    db.delete(role)
    db.commit()
