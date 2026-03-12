import os
import json
import hmac
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "PetAdoptionSystem-GraduationProject-SecretKey")


def _hash_password_sha256(password: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def get_password_hash(password: str) -> str:
    """生成密码哈希（纯标准库实现）"""
    salt = secrets.token_hex(8)
    return _hash_password_sha256(password, salt)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确 (兼容明文与当前 sha256 方案)"""
    # 历史明文
    if "$" not in hashed_password:
        return plain_password == hashed_password

    # 当前哈希格式: sha256$salt$hexdigest
    parts = hashed_password.split("$")
    if len(parts) == 3 and parts[0] == "sha256":
        _, salt, _ = parts
        return hmac.compare_digest(_hash_password_sha256(plain_password, salt), hashed_password)

    # 其他历史格式（如 bcrypt）当前环境缺少依赖时，返回 False 而非抛错
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建轻量签名 token（无第三方依赖）"""
    payload = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    payload.update({"exp": int(expire.timestamp())})
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def decode_access_token(token: str) -> Optional[dict]:
    """解析并验证 token"""
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None

        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.utcnow().timestamp()):
            return None
        return payload
    except Exception:
        return None
