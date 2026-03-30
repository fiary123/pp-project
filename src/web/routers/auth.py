from fastapi import APIRouter, HTTPException, Request
from src.web.schemas import LoginRequest, RegisterRequest, SendCodeRequest
from src.web.services.db_service import get_db, ensure_tables
from src.web.services.auth_service import get_password_hash, verify_password, create_access_token
from src.web.limiter import limiter
import sqlite3
import random
import string
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["auth"])

def send_email(to_email: str, code: str):
    """发送邮件逻辑（支持测试模式）"""
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not smtp_user or not smtp_pass:
        print(f"\n[TEST MODE] 验证码发送至 {to_email}: {code}\n")
        return True

    try:
        msg = MIMEText(f"您的注册验证码为：{code}，有效期5分钟。请勿泄露给他人。", "plain", "utf-8")
        msg["Subject"] = "【智慧宠物平台】注册验证码"
        msg["From"] = smtp_user
        msg["To"] = to_email

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

@router.post("/send-code")
@limiter.limit("2/minute")
async def send_code(request: Request, req: SendCodeRequest):
    code = "".join(random.choices(string.digits, k=6))
    expire_at = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO email_codes (email, code, expire_at) VALUES (?, ?, ?)",
            (req.email, code, expire_at)
        )
        conn.commit()
    
    if send_email(req.email, code):
        return {"status": "success", "message": "验证码已发送"}
    else:
        raise HTTPException(status_code=500, detail="邮件发送失败，请稍后再试")

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (req.email,))
        user = cursor.fetchone()

    if user and verify_password(req.password, user["password"]):
        access_token = create_access_token(data={"sub": str(user["id"])})
        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            }
        }
    raise HTTPException(status_code=401, detail="邮箱或密码错误")

@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest):
    with get_db() as conn:
        # 1. 校验验证码
        cursor = conn.cursor()
        cursor.execute("SELECT code, expire_at FROM email_codes WHERE email = ?", (req.email,))
        record = cursor.fetchone()
        
        if not record:
            raise HTTPException(status_code=400, detail="请先获取验证码")
        
        saved_code, expire_at = record
        if saved_code != req.code:
            raise HTTPException(status_code=400, detail="验证码错误")
        
        if datetime.now() > datetime.strptime(expire_at, "%Y-%m-%d %H:%M:%S"):
            raise HTTPException(status_code=400, detail="验证码已过期")

        # 2. 注册用户
        hashed_pwd = get_password_hash(req.password)
        try:
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (req.username, req.email, hashed_pwd, "user"),
            )
            # 注册成功后删除验证码，防止复用
            conn.execute("DELETE FROM email_codes WHERE email = ?", (req.email,))
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="邮箱已注册")
            
    return {"status": "success"}
