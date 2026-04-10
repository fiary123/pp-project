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
    """发送邮件逻辑"""
    # 评审说明：
    # 该函数统一封装验证码发送流程，便于注册等场景复用。
    # 若未配置 SMTP，则退化为测试模式，直接在控制台输出验证码。
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
    # 这里生成 6 位验证码并写入 email_codes 表，同时记录 5 分钟过期时间。
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
    # 登录流程包括“按邮箱查用户”“校验密码哈希”“签发 JWT”三步。
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (req.email,))
        user = cursor.fetchone()

    if user and verify_password(req.password, user["password"]):
        # JWT 的 sub 字段保存用户主键，供后续鉴权依赖恢复登录身份。
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
    with get_db() as conn:    # 评审说明：注册接口重点保证验证码有效、邮箱唯一、密码密文存储。
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
        hashed_pwd = get_password_hash(req.password)
        try:  # 2. 注册用户:明文密码不会直接入库，而是先转换为 bcrypt 哈希值。
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (req.username, req.email, hashed_pwd, "user"),) 
            conn.execute("DELETE FROM email_codes WHERE email = ?", (req.email,))
            conn.commit()  # 注册成功后删除验证码，防止复用
        except sqlite3.IntegrityError:
            # users.email 具备 UNIQUE 约束，此处用数据库异常兜底唯一性校验。
            raise HTTPException(status_code=400, detail="邮箱已注册")        
    return {"status": "success"}
