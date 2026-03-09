from fastapi import APIRouter, HTTPException, Depends
from src.web.schemas import LoginRequest, RegisterRequest
from src.web.services.db_service import get_db_connection, ensure_tables
from src.web.services.auth_service import get_password_hash, verify_password, create_access_token
import sqlite3
from datetime import timedelta

router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/login")
async def login(req: LoginRequest):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    # 先根据邮箱查用户
    cursor.execute("SELECT * FROM users WHERE email = ?", (req.email,))
    user = cursor.fetchone()
    conn.close()
    
    # 验证密码哈希
    if user and verify_password(req.password, user["password"]):
        # 创建 Token
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
async def register(req: RegisterRequest):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    hashed_pwd = get_password_hash(req.password)
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (req.username, req.email, hashed_pwd, req.role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="邮箱已注册")
    conn.close()
    return {"status": "success"}
