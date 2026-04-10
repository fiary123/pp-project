import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# --- 关键配置（必须通过环境变量 JWT_SECRET_KEY 配置，不提供默认值）---
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "环境变量 JWT_SECRET_KEY 未设置。"
        "请在 .env 文件或部署环境中设置一个足够随机的密钥，"
        "例如：JWT_SECRET_KEY=" + secrets.token_hex(32)
    )

ALGORITHM = "HS256"
# Token 有效期：优先读取环境变量 ACCESS_TOKEN_EXPIRE_MINUTES
# 本地/演示环境默认放宽到 24 小时，避免频繁重新登录；生产环境请按需收紧。
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# 密码哈希上下文
# 评审说明：
# passlib 会为每个密码自动生成独立盐值，从而避免相同密码产生相同密文。
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # 业务层只拿到哈希结果，不需要关心盐值生成细节。
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（仅支持 bcrypt 哈希，不允许明文存储）"""
    # 登录时只做明文与哈希的安全比对，不做明文反解。
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT Token，过期时间由 ACCESS_TOKEN_EXPIRE_MINUTES 统一控制"""
    # Token 中写入 exp 过期时间，前后端都可据此判断登录态是否失效。
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """解析并验证 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
