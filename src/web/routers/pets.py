from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from src.web.schemas import PetBatchCreate
from src.web.services.db_service import get_db
from src.web.dependencies import get_current_user, get_optional_user

router = APIRouter(prefix='/api', tags=['pets'])

@router.get('/pets')
def get_pets(location: Optional[str] = Query(None, description="按地区筛选"), current_user: Optional[dict] = Depends(get_optional_user)):
    """
    获取宠物列表，聚合详细特征、领养要求及送养人信息
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        base_query = """
            SELECT
                p.*,
                u.username AS owner_name, u.email AS owner_email,
                f.age_stage, f.gender AS feature_gender, f.health_status, f.sterilized,
                f.energy_level, f.care_level, f.beginner_friendly, f.social_level,
                f.temperament_tags, f.good_with_children, f.good_with_other_pets,
                f.medical_needs, f.companionship_need, f.budget_need_level, f.special_care_flag,
                r.allow_beginner, r.min_budget_level, r.min_companion_hours, r.required_housing_type,
                r.forbid_other_pets, r.forbid_children, r.require_experience,
                r.require_stable_housing, r.require_return_visit, r.region_limit, r.special_notes
            FROM pets p
            JOIN users u ON p.owner_id = u.id
            LEFT JOIN pet_features f ON p.id = f.pet_id
            LEFT JOIN pet_requirements r ON p.id = r.pet_id
        """
        
        params = []
        if location:
            base_query += " WHERE p.location LIKE ?"
            params.append(f"%{location}%")
            
        base_query += " ORDER BY p.id DESC"
        
        cursor.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]

        # 处理联系方式可见性
        if current_user:
            uid = current_user['id']
            # 查询该用户已通过的申请 (状态必须是 approved 或后续状态)
            cursor.execute("""
                SELECT pet_id FROM applications 
                WHERE user_id = ? AND status IN ('approved', 'adopted', 'followup_completed')
            """, (uid,))
            approved_pet_ids = {row[0] for row in cursor.fetchall()}
            
            for p in results:
                # 只有宠物主人或已通过审核的申请人能看联系方式
                if p['owner_id'] != uid and p['id'] not in approved_pet_ids:
                    p['owner_contact_hidden'] = True
                    # 强力遮写敏感邮箱
                    email_parts = p['owner_email'].split('@')
                    p['owner_email'] = f"{email_parts[0][0]}***@{email_parts[1]}"
                else:
                    p['owner_contact_hidden'] = False
        else:
            for p in results:
                p['owner_contact_hidden'] = True
                p['owner_email'] = "***@***.com"

        return results
