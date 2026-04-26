import json
from fastapi import APIRouter, HTTPException, Depends
from src.web.schemas import PostCreate, PostUpdate, CommentCreate
from src.web.services.db_service import get_db
from src.web.dependencies import get_current_user

router = APIRouter(prefix='/api/posts', tags=['posts'])


@router.get('')
def get_posts():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT p.*, u.username, u.role FROM posts p '
            'JOIN users u ON p.user_id = u.id ORDER BY p.create_time DESC'
        )
        return [dict(row) for row in cursor.fetchall()]


@router.post('')
async def create_post(req: PostCreate, current_user: dict = Depends(get_current_user)):
    """
    创建帖子。
    当 type == 'adopt_help' (送养帖) 时，自动同步创建 pets + pet_features + pet_requirements 记录。
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. 存帖子（全部字段）
        prefs_json = json.dumps(req.adoption_preferences, ensure_ascii=False) if req.adoption_preferences else None
        cursor.execute(
            """INSERT INTO posts
               (user_id, title, content, image_url, image_urls, type,
                pet_name, pet_gender, pet_age, pet_breed, adopt_reason, location)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                current_user['id'], req.title, req.content,
                req.image_url, req.image_urls, req.type,
                req.pet_name, req.pet_gender, req.pet_age,
                req.pet_breed, req.adopt_reason, req.location,
            ),
        )
        post_id = cursor.lastrowid

        # 2. 送养帖 → 同步创建宠物记录 + 特征 + 约束
        pet_id = None
        if req.type == 'adopt_help' and req.pet_name:
            species = _infer_species(req.pet_breed)
            cursor.execute(
                """INSERT INTO pets
                   (owner_id, source_post_id, owner_type, name, species,
                    description, image_url, image_urls, status)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    current_user['id'], post_id, 'personal',
                    req.pet_name, species,
                    req.content[:200] if req.content else '',
                    req.image_url,
                    req.image_urls,
                    '待领养',
                ),
            )
            pet_id = cursor.lastrowid

            # pet_features
            gender_map = {'male': '公', 'female': '母'}
            cursor.execute(
                """INSERT INTO pet_features
                   (pet_id, species, gender, age_stage, health_status, sterilized,
                    energy_level, temperament_tags, beginner_friendly,
                    good_with_children, good_with_other_pets)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    pet_id, species,
                    gender_map.get(req.pet_gender, '未知'),
                    _infer_age_stage(req.pet_age),
                    '健康', 0, '中', '亲人, 温顺', 1, 1, 1,
                ),
            )

            # pet_requirements (深度对齐评估引擎要求)
            prefs = req.adoption_preferences or {}
            cursor.execute(
                """INSERT INTO pet_requirements
                   (pet_id, allow_beginner, min_budget_level, min_companion_hours,
                    required_housing_type, forbid_other_pets, forbid_children,
                    require_stable_housing, require_return_visit, special_notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    pet_id,
                    1 if prefs.get('allow_novice', True) else 0,
                    prefs.get('min_budget_level', '中'),
                    float(prefs.get('min_companion_hours', 2.0)),
                    prefs.get('required_housing_type', '公寓'),
                    1 if prefs.get('forbid_other_pets') else 0,
                    1 if prefs.get('forbid_children') else 0,
                    1 if prefs.get('require_stable_housing') else 0,
                    1 if prefs.get('require_followup_updates', True) else 0,
                    prefs.get('special_notes', '')
                ),
            )

            # publisher_preferences
            cursor.execute(
                """INSERT OR REPLACE INTO publisher_preferences
                   (publisher_id, pet_id, risk_tolerance, raw_preferences_json)
                   VALUES (?,?,?,?)""",
                (
                    current_user['id'], pet_id,
                    prefs.get('risk_tolerance', 'medium'),
                    json.dumps(prefs, ensure_ascii=False),
                ),
            )

        conn.commit()
        return {'status': 'success', 'post_id': post_id, 'pet_id': pet_id}


@router.put('/{post_id}')
async def update_post(post_id: int, req: PostUpdate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='帖子不存在')
        if row['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail='无权编辑')

        cursor.execute(
            """UPDATE posts SET
               title=COALESCE(?,title), content=COALESCE(?,content),
               image_url=COALESCE(?,image_url), image_urls=COALESCE(?,image_urls),
               pet_name=COALESCE(?,pet_name), pet_gender=COALESCE(?,pet_gender),
               pet_age=COALESCE(?,pet_age), pet_breed=COALESCE(?,pet_breed),
               adopt_reason=COALESCE(?,adopt_reason), location=COALESCE(?,location)
               WHERE id=?""",
            (
                req.title, req.content, req.image_url, req.image_urls,
                req.pet_name, req.pet_gender, req.pet_age, req.pet_breed,
                req.adopt_reason, req.location, post_id,
            ),
        )
        conn.commit()
    return {'status': 'success'}


@router.delete('/{post_id}')
async def delete_post(post_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='帖子不存在')
        if row['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail='无权删除')

        cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
    return {'status': 'success'}


@router.post('/{post_id}/like')
async def like_post(post_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE posts SET likes = COALESCE(likes,0) + 1 WHERE id = ?', (post_id,))
        conn.commit()
    return {'status': 'success'}


@router.get('/{post_id}/comments')
def get_comments(post_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT c.*, u.username FROM comments c '
            'JOIN users u ON c.user_id = u.id '
            'WHERE c.post_id = ? ORDER BY c.create_time ASC',
            (post_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


@router.post('/comment')
async def create_comment(req: CommentCreate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO comments (post_id, user_id, content) VALUES (?,?,?)',
            (req.post_id, current_user['id'], req.content),
        )
        conn.commit()
    return {'status': 'success'}


# --- 辅助函数 ---

def _infer_species(breed: str | None) -> str:
    if not breed:
        return '猫'
    breed_lower = breed.lower()
    dog_keywords = ['犬', '狗', '柴', '金毛', '拉布拉多', '哈士奇', '泰迪', '柯基', '边牧', '萨摩']
    if any(k in breed_lower for k in dog_keywords):
        return '狗'
    return '猫'


def _infer_age_stage(age_str: str | None) -> str:
    if not age_str:
        return '成年'
    if any(k in age_str for k in ['月', '幼', '奶']):
        return '幼年'
    if any(k in age_str for k in ['老', '10', '11', '12', '13', '14', '15']):
        return '老年'
    return '成年'
