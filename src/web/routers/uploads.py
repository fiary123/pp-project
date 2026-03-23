import os
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["uploads"])

UPLOAD_DIR = Path("static/uploads")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (支持视频上传)
ALLOWED_MIME_PREFIXES = (
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm", "video/ogg"
)
MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
}

# 通过文件魔数（magic bytes）检测真实类型，不依赖扩展名
MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",   # RIFF....WEBP
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"\x00\x00\x00\x18ftypmp42": "video/mp4",
    b"\x00\x00\x00\x20ftypmp42": "video/mp4",
    b"\x1a\x45\xdf\xa3": "video/webm",
}


def detect_mime_type(header: bytes) -> str | None:
    for sig, mime in MAGIC_SIGNATURES.items():
        if header.startswith(sig):
            return mime
    # WEBP 额外检测
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    # MP4 更多变种检测 (简单粗暴的查找 ftyp 关键字)
    if b"ftyp" in header[:20]:
        return "video/mp4"
    return None


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    # 1. 读取文件内容
    contents = await file.read()

    # 2. 文件大小校验
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB")

    # 3. 通过魔数检测真实 MIME 类型（防止伪装扩展名绕过）
    mime_type = detect_mime_type(contents[:16])
    if mime_type not in ALLOWED_MIME_PREFIXES:
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅允许上传图片（JPEG/PNG/WebP/GIF）")

    # 4. 用 UUID 生成文件名，完全忽略原始文件名（防路径遍历）
    ext = MIME_TO_EXT[mime_type]
    new_filename = f"{uuid.uuid4()}{ext}"

    # 5. 确保上传目录存在
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / new_filename

    # 6. 写入文件
    file_path.write_bytes(contents)

    url = f"/static/uploads/{new_filename}"
    return {"status": "success", "url": url}
