from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from src.web.services.auth_service import decode_access_token
from src.web.services.db_service import get_db_connection

# 定义获取 token 的方式 (这里使用标准的 OAuth2 流程，会自动从 Authorization: Bearer <token> 获取)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)

def _load_user_from_token(token: str):
    """解析 token 并返回当前用户对象；解析失败时返回 None。"""
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id: int = payload.get("sub")
    if user_id is None:
        return None

    # 从数据库加载完整用户信息
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, status FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        return None

    user_dict = dict(user)
    if user_dict.get("status") == "banned":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您的账号已被禁用")

    return user_dict


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """验证 Token 并返回当前用户对象"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _load_user_from_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期或无效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(token: str = Depends(oauth2_scheme)):
    """可选登录态：未登录或 token 无效时返回 None。"""
    return _load_user_from_token(token)

async def require_admin(current_user: dict = Depends(get_current_user)):
    """权限校验：要求必须是 admin 角色"""
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅限系统管理员访问"
        )
    return current_user
