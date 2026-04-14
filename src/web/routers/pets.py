from fastapi import APIRouter, HTTPException, Depends
import json
from src.web.schemas import PetUpdate, PetBatchCreate, PetFeatureUpdate, PetRequirementUpdate
from src.web.services.db_service import get_db
from src.web.services.profile_service import ProfileService
from src.web.dependencies import get_current_user
from src.agents.agents import analyze_pet_features

router = APIRouter(prefix="/api", tags=["pets"])


@router.post("/pets/batch")
async def batch_create_pets(req: PetBatchCreate, current_user: dict = Depends(get_current_user)):
    """机构批量录入流浪动物，同时利用 Agent 自动提取推荐特征并生成送养帖子"""
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
            # 1. 插入基础表
            cursor.execute(
                """INSERT INTO pets (owner_id, owner_type, name, species, age, description, image_url, tags, status)
                   VALUES (?, 'org', ?, ?, ?, ?, ?, ?, '待领养')""",
                (req.owner_id, pet.name, pet.species, pet.age,
                 pet.description, pet.image_url, pet.tags or "[]"),
            )
            pet_id = cursor.lastrowid

            # 2. [重构重点]：调用 Agent 自动提取结构化推荐特征 (异步执行)
            try:
                # 在真实生产环境，这里通常入任务队列。此处同步调用演示联动。
                extracted = await analyze_pet_features(
                    pet_name=pet.name,
                    pet_species=pet.species,
                    description=pet.description or ""
                )
                
                # 写入 pet_features
                ProfileService.update_pet_features(pet_id, PetFeatureUpdate(**{
                    "age_stage": extracted.get("age_stage"),
                    "size_level": extracted.get("size_level"),
                    "activity_level": extracted.get("activity_level"),
                    "care_difficulty": extracted.get("care_difficulty"),
                    "good_with_children": extracted.get("good_with_children"),
                    "good_with_other_pets": extracted.get("good_with_other_pets"),
                    "companionship_need": extracted.get("companionship_need"),
                    "budget_need_level": extracted.get("budget_need_level"),
                    "sterilized": extracted.get("sterilized"),
                    "temperament_tags": extracted.get("temperament_tags")
                }))
                
                # 写入 pet_requirements
                ProfileService.update_pet_requirements(pet_id, PetRequirementUpdate(**{
                    "allow_beginner": extracted.get("allow_beginner"),
                    "min_companion_hours": extracted.get("min_companion_hours"),
                    "required_housing_type": extracted.get("required_housing_type")
                }))
            except Exception as e:
                print(f"Auto-extraction failed for pet {pet_id}: {e}")

            # 3. 自动生成对应的送养帖
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

from src.agents.agents import analyze_pet_features
# ... (保持现有导入)

@router.post("/pets/{pet_id}/auto-extract")
async def auto_extract_pet_features(pet_id: int, current_user: dict = Depends(get_current_user)):
    """利用 AI 智能提取宠物的结构化特征"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, species, description, owner_id FROM pets WHERE id=?", (pet_id,))
        pet = cursor.fetchone()
        if not pet:
            raise HTTPException(status_code=404, detail="宠物不存在")
        if pet["owner_id"] != current_user["id"] and current_user.get("role") not in ["admin", "org_admin"]:
            raise HTTPException(status_code=403, detail="无权限执行提取操作")

    # 调用 AI Agent 提取特征
    extracted = await analyze_pet_features(
        pet_name=pet["name"],
        pet_species=pet["species"],
        description=pet["description"] or ""
    )
    
    # 转化为 PetFeatureUpdate 对象并保存
    from src.web.schemas import PetFeatureUpdate
    feature_update = PetFeatureUpdate(
        energy_level=extracted.get("energy_level"),
        care_level=extracted.get("care_level"),
        beginner_friendly=extracted.get("beginner_friendly"),
        social_level=extracted.get("social_level"),
        special_care_flag=extracted.get("special_care_flag")
    )
    
    ProfileService.update_pet_features(pet_id, feature_update)
    
    # 更新宠物表的 tags 字段 (可选)
    if extracted.get("tags"):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pets SET tags = ? WHERE id = ?", (json.dumps(extracted["tags"], ensure_ascii=False), pet_id))
            conn.commit()

    return {
        "status": "success",
        "message": "AI 智能提取成功",
        "extracted_features": extracted
    }

@router.put("/pets/{pet_id}/feature")
async def update_pet_feature(pet_id: int, features: PetFeatureUpdate, current_user: dict = Depends(get_current_user)):
    """更新宠物推荐特征"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id FROM pets WHERE id=?", (pet_id,))
        pet = cursor.fetchone()
        if not pet:
            raise HTTPException(status_code=404, detail="宠物不存在")
        if pet["owner_id"] != current_user["id"] and current_user.get("role") not in ["admin", "org_admin"]:
            raise HTTPException(status_code=403, detail="无权限修改该宠物特征")
    
    ProfileService.update_pet_features(pet_id, features)
    return {"message": "宠物特征更新成功"}

@router.get("/pets/{pet_id}/requirement")
async def get_pet_requirement(pet_id: int):
    """获取宠物领养要求"""
    reqs = ProfileService.get_pet_requirements(pet_id)
    return reqs if reqs else {}

@router.put("/pets/{pet_id}/requirement")
async def update_pet_requirement(pet_id: int, reqs: PetRequirementUpdate, current_user: dict = Depends(get_current_user)):
    """更新宠物领养要求"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id FROM pets WHERE id=?", (pet_id,))
        pet = cursor.fetchone()
        if not pet:
            raise HTTPException(status_code=404, detail="宠物不存在")
        if pet["owner_id"] != current_user["id"] and current_user.get("role") not in ["admin", "org_admin"]:
            raise HTTPException(status_code=403, detail="无权限修改该宠物领养要求")
            
    ProfileService.update_pet_requirements(pet_id, reqs)
    return {"message": "领养要求更新成功"}
