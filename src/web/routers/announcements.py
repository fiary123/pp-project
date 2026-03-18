from fastapi import APIRouter, HTTPException, Depends
from src.web.schemas import AnnouncementCreate
from src.web.services.db_service import get_db
from src.web.dependencies import require_admin
from datetime import datetime

router = APIRouter(prefix="/api", tags=["announcements"])


@router.get("/announcements")
def get_announcements():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM announcements ORDER BY date DESC")
        res = [dict(row) for row in cursor.fetchall()]
    return res


@router.post("/announcements")
async def create_announcement(req: AnnouncementCreate, current_user: dict = Depends(require_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO announcements (title, content, is_hot, date) VALUES (?, ?, ?, ?)",
            (req.title, req.content, req.is_hot, datetime.now().strftime("%Y-%m-%d")),
        )
        conn.commit()
    return {"status": "success"}


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: int, current_user: dict = Depends(require_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM announcements WHERE id=?", (announcement_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="公告不存在")
        cursor.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
        conn.commit()
    return {"status": "success"}
