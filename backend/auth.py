from datetime import datetime, timedelta
from typing import Optional, List, Dict
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt

# Config
SECRET_KEY = os.environ.get("BESCOM_SECRET_KEY", "change-this-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Simple in-memory token blacklist (demo only)
_token_blacklist = set()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = []


class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    roles: List[str] = []


class UserInDB(User):
    hashed_password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Demo in-memory users; replace with real user store in production
_users_db: Dict[str, Dict] = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "hashed_password": get_password_hash("adminpass"),
        "roles": ["Admin"],
    },
    "operator": {
        "username": "operator",
        "full_name": "Operator User",
        "hashed_password": get_password_hash("operatorpass"),
        "roles": ["Operator"],
    },
    "auditor": {
        "username": "auditor",
        "full_name": "Auditor User",
        "hashed_password": get_password_hash("auditorpass"),
        "roles": ["Auditor"],
    },
}


def get_user(username: str) -> Optional[UserInDB]:
    u = _users_db.get(username)
    if not u:
        return None
    return UserInDB(**u)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    if token in _token_blacklist:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        roles = payload.get("roles", [])
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=roles)
    except JWTError:
        raise credentials_exception
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    return User(username=user.username, full_name=user.full_name, roles=user.roles)


def require_roles(*allowed_roles: str):
    def role_dependency(current_user: User = Depends(get_current_user)):
        if not any(r in current_user.roles for r in allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_dependency


router = APIRouter(prefix="/api/auth", tags=["auth"]) 


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user.username, "roles": user.roles})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    _token_blacklist.add(token)
    return {"status": "ok", "message": "token revoked"}


# Example protected endpoints
@router.get("/protected/admin")
async def admin_only(current_user: User = Depends(require_roles("Admin"))):
    return {"msg": "welcome admin", "user": current_user.username}


@router.get("/protected/operator")
async def operator_or_admin(current_user: User = Depends(require_roles("Operator", "Admin"))):
    return {"msg": "operator endpoint", "user": current_user.username}


@router.get("/protected/auditor")
async def auditor_or_admin(current_user: User = Depends(require_roles("Auditor", "Admin"))):
    return {"msg": "auditor endpoint", "user": current_user.username}
