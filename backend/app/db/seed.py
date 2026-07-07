import logging

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.permissions import DEFAULT_QA_PERMS, Perm
from ..core.security import hash_password
from . import models

log = logging.getLogger(__name__)


def seed(db: Session) -> None:
    """Idempotent startup seed: sync permission enum, ensure admin/qa roles,
    create the initial admin user from env on an empty user table."""
    perms = {p.code: p for p in db.query(models.Permission).all()}
    for code in [p.value for p in Perm]:
        if code not in perms:
            perm = models.Permission(code=code)
            db.add(perm)
            perms[code] = perm
    db.flush()

    admin_role = db.query(models.Role).filter_by(name="admin").first()
    if not admin_role:
        admin_role = models.Role(name="admin", description="Full access")
        db.add(admin_role)
    admin_role.permissions = list(perms.values())  # admin always has every permission

    qa_role = db.query(models.Role).filter_by(name=settings.ldap_default_role).first()
    if not qa_role:
        qa_role = models.Role(
            name=settings.ldap_default_role,
            description="Default role for LDAP-provisioned users",
            permissions=[perms[p.value] for p in DEFAULT_QA_PERMS],
        )
        db.add(qa_role)

    if settings.admin_username and settings.admin_password:
        user = db.query(models.User).filter_by(username=settings.admin_username).first()
        if not user:
            db.add(
                models.User(
                    username=settings.admin_username,
                    hashed_password=hash_password(settings.admin_password),
                    auth_source="local",
                    roles=[admin_role],
                )
            )
            log.info("Created initial admin user %r", settings.admin_username)

    db.commit()
