from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..Databases import models, database
from .ldap_handler import verify_ldap_credentials
import os

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Check local DB for user existence (even if LDAP, we might want a shadow record or just trust the token)
    # For this implementation, we'll check if user exists in DB. 
    # If LDAP user logs in for first time, we might create a record.
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        # If it was a valid token, maybe user was deleted? Or it's an LDAP user not yet in DB?
        # For now, strict check.
        raise credentials_exception
    return user

def authenticate_user(db: Session, username: str, password: str):
    # 1. Try Local Auth (Admin/Local users)
    user = db.query(models.User).filter(models.User.username == username).first()
    
    if user and user.auth_source == "local":
        if verify_password(password, user.hashed_password):
            return user
        else:
            return False # Password mismatch
            
    # 2. Try LDAP Auth
    # If user exists and is configured for LDAP, or if user doesn't exist (auto-provisioning?)
    # Let's assume if user is in DB as 'ldap' or not in DB, we try LDAP.
    
    if verify_ldap_credentials(username, password):
        # LDAP Success
        if not user:
            # Auto-provision user in local DB
            user = models.User(username=username, auth_source="ldap", is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
        
    return False
