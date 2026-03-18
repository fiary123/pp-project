from fastapi import APIRouter, HTTPException, Request
from src.web.schemas import LoginRequest, RegisterRequest
from src.web.services.db_service import get_db, ensure_tables
from src.web.services.auth_service import get_password_hash, verify_password, create_access_token
from src.web.limiter import limiter
import sqlite3

router = APIRouter(prefix="/api", tags=["auth"])

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
    hashed_pwd = get_password_hash(req.password)
    with get_db() as conn:
        ensure_tables(conn)
        try:
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (req.username, req.email, hashed_pwd, req.role),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="邮箱已注册")
    return {"status": "success"}
