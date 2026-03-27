from fastapi import APIRouter, HTTPException, Depends
from src.web.schemas import PetUpdate, PetBatchCreate
from src.web.services.db_service import get_db
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["pets"])


@router.post("/pets/batch")
async def batch_create_pets(req: PetBatchCreate, current_user: dict = Depends(get_current_user)):
    """机构批量录入流浪动物，同时自动生成对应的送养帖子"""
    if current_user.get("role") != "org_admin":
        raise HTTPException(status_code=403, detail="仅救助站管理员可批量录入动物")
    if req.owner_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="owner_id 与当前用户不符")
    if not req.pets:
        raise HTTPException(status_code=400, detail="至少需要一条动物记录")

    created = []
    with get_db() as conn:
        cursor = conn.cursor()
        for pet in req.pets:
            cursor.execute(
                """INSERT INTO pets (owner_id, owner_type, name, species, age, description, image_url, tags, status)
                   VALUES (?, 'org', ?, ?, ?, ?, ?, ?, '待领养')""",
                (req.owner_id, pet.name, pet.species, pet.age,
                 pet.description, pet.image_url, pet.tags or "[]"),
            )
            pet_id = cursor.lastrowid

            # 自动生成对应的送养帖
            gender_label = {"male": "雄性", "female": "雌性"}.get(pet.gender, "性别未知")
            auto_title = f"【{pet.species}送养】{pet.name}"
            auto_content = (
                f"**{pet.name}**  {gender_label} · {pet.age}岁\n\n"
                + (pet.description or "暂无描述") + "\n\n"
                + (f"📍 所在地：{pet.location}" if pet.location else "")
            ).strip()

            cursor.execute(
                """INSERT INTO posts (user_id, title, content, type, image_url, pet_name, pet_gender, pet_age, pet_breed, location)
                   VALUES (?, ?, ?, 'adopt', ?, ?, ?, ?, ?, ?)""",
                (req.owner_id, auto_title, auto_content,
                 pet.image_url, pet.name, pet.gender,
                 str(pet.age) + "岁", pet.species, pet.location),
            )
            created.append({"pet_id": pet_id, "name": pet.name})
        conn.commit()
    return {"status": "success", "created": created, "count": len(created)}


@router.get("/pets")
def get_all_pets():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.*,
                   po.image_url AS post_image_url,
                   po.image_urls AS post_image_urls,
                   po.pet_gender,
                   po.pet_age,
                   po.pet_breed,
                   po.adopt_reason,
                   po.location,
                   po.title AS post_title,
                   po.content AS post_content
            FROM pets p
            LEFT JOIN posts po ON po.id = p.source_post_id
            ORDER BY p.created_at DESC, p.id DESC
            """
        )
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
            """UPDATE pets SET
               name=COALESCE(?,name),
               species=COALESCE(?,species),
               image_url=COALESCE(?,image_url),
               description=COALESCE(?,description),
               adoption_preferences=COALESCE(?,adoption_preferences)
               WHERE id=?""",
            (req.name, req.species, req.image_url, req.description, req.adoption_preferences, pet_id),
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
