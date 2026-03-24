from fastapi import APIRouter, HTTPException, Depends
from src.web.schemas import PetUpdate
from src.web.services.db_service import get_db
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["pets"])


@router.get("/pets")
def get_all_pets():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pets")
        res = [dict(row) for row in cursor.fetchall()]
    return res


@router.put("/pets/{pet_id}")
async def update_pet(pet_id: int, req: PetUpdate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id FROM pets WHERE id=?", (pet_id,))
        pet = cursor.fetchone()
        if not pet:
            raise HTTPException(status_code=404, detail="宠物不存在")
        if pet["owner_id"] != current_user["id"] and current_user.get("role") not in ["org_admin"]:
            raise HTTPException(status_code=403, detail="无权限修改该宠物信息")
        cursor.execute(
            "UPDATE pets SET name=COALESCE(?,name), species=COALESCE(?,species), image_url=COALESCE(?,image_url), description=COALESCE(?,description) WHERE id=?",
            (req.name, req.species, req.image_url, req.description, pet_id),
        )
        conn.commit()
    return {"status": "success"}


@router.delete("/pets/{pet_id}")
async def delete_pet(pet_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id FROM pets WHERE id=?", (pet_id,))
        pet = cursor.fetchone()
        if not pet:
            raise HTTPException(status_code=404, detail="宠物不存在")
        if pet["owner_id"] != current_user["id"] and current_user.get("role") not in ["org_admin"]:
            raise HTTPException(status_code=403, detail="无权限删除该宠物")
        cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
        conn.commit()
    return {"status": "success"}
