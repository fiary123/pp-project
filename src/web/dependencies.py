from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from src.web.services.auth_service import decode_access_token
from src.web.services.db_service import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_exception
    
    user_id = payload.get("sub")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user is None:
            raise credentials_exception
        return dict(user)

async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[dict]:
    """
    可选登录依赖项。
    如果提供了有效的 Token，则返回用户信息；否则返回 None。
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            return None
        
        user_id = payload.get("sub")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, role FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
    except Exception:
        return None

# --- 简化版两级权限体系 ---

def require_admin(current_user: dict = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅限管理员访问"
        )
    return current_user

def require_user(current_user: dict = Depends(get_current_user)):
    """要求登录用户即可"""
    return current_user
