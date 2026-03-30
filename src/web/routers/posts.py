import json
import re

from fastapi import APIRouter, HTTPException, Depends
from src.web.schemas import PostCreate, PostUpdate, CommentCreate
from src.web.services.db_service import get_db, ensure_tables
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["posts"])

DEMO_COMMENT_TEXTS = {
    "这张抓拍太有氛围了，狗狗状态也很好。",
    "它们玩了好久，回家都累坏啦。",
    "收藏了，正准备接第一只猫回家。",
    "真的好可爱，希望它能尽快遇到合适的家。",
    "目前状态稳定，已完成基础驱虫。",
}


def _ensure_demo_posts(cursor):
    cursor.execute("SELECT id, role, username FROM users WHERE role IN ('individual', 'org_admin') ORDER BY id ASC")
    users = [dict(row) for row in cursor.fetchall()]
    if not users:
        return

    individual = next((u for u in users if u["role"] == "individual"), users[0])
    demo_posts = [
        {
            "title": "今天在公园遇到了超可爱的柴犬！",
            "content": "今天带我家主子去公园散步，结果遇到了一只超热情的柴犬，两只小可爱玩得不亦乐乎。",
            "image_url": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1200&q=80",
            "type": "daily",
            "likes": 12,
            "user_id": individual["id"],
        },
        {
            "title": "新手养猫避坑指南",
            "content": "作为一名有着5年养猫经验的博主，今天要给各位新手家长排排雷。建议收藏！",
            "image_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=1200&q=80",
            "type": "experience",
            "likes": 18,
            "user_id": individual["id"],
        },
        {
            "title": "【急寻领养】温顺橘猫寻找温暖的家",
            "content": "在小区楼下发现的小橘，大概3个月大，已做完基础驱虫。性格超级粘人。",
            "image_url": "https://images.unsplash.com/photo-1548247416-ec66f4900b2e?auto=format&fit=crop&w=1200&q=80",
            "type": "adopt_help",
            "likes": 26,
            "user_id": individual["id"],
            "pet_name": "小橘",
            "pet_gender": "unknown",
            "pet_age": "3个月",
            "pet_breed": "橘猫",
            "adopt_reason": "小区救助后暂时安置，现希望找到长期稳定的家庭。",
            "location": "成都市高新区",
        },
    ]

    for post in demo_posts:
        cursor.execute("SELECT id FROM posts WHERE title=? AND type=?", (post["title"], post["type"]))
        existing = cursor.fetchone()
        if existing:
            post_id = existing["id"]
        else:
            cursor.execute(
                """
                INSERT INTO posts
                (user_id, title, content, image_url, image_urls, type, pet_name, pet_gender, pet_age, pet_breed, adopt_reason, location, likes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post["user_id"],
                    post["title"],
                    post["content"],
                    post["image_url"],
                    json.dumps([post["image_url"]], ensure_ascii=False),
                    post["type"],
                    post.get("pet_name"),
                    post.get("pet_gender"),
                    post.get("pet_age"),
                    post.get("pet_breed"),
                    post.get("adopt_reason"),
                    post.get("location"),
                    post["likes"],
                ),
            )
            post_id = cursor.lastrowid

        cursor.execute(
            "DELETE FROM comments WHERE post_id=? AND content IN ({})".format(",".join(["?"] * len(DEMO_COMMENT_TEXTS))),
            (post_id, *DEMO_COMMENT_TEXTS),
        )


def _default_adoption_preferences():
    return {
        "hard_preferences": [],
        "soft_preferences": ["住房稳定性", "陪伴时间", "责任意识"],
        "allow_novice": True,
        "accept_renting": True,
        "require_stable_housing": False,
        "require_financial_capacity": False,
        "prefer_local": False,
        "require_family_agreement": False,
        "prefer_quiet_household": False,
        "prefer_multi_pet_experience": False,
        "focus_experience": False,
        "focus_companionship": True,
        "focus_stability": True,
        "risk_tolerance": "medium",
    }


def _normalize_adoption_preferences(raw_value):
    pref = _default_adoption_preferences()
    if isinstance(raw_value, str):
        try:
            raw_value = json.loads(raw_value)
        except Exception:
            raw_value = None
    if isinstance(raw_value, dict):
        pref.update(raw_value)
    pref["hard_preferences"] = list(dict.fromkeys(pref.get("hard_preferences") or []))
    pref["soft_preferences"] = list(dict.fromkeys(pref.get("soft_preferences") or []))
    return pref


def _sync_preference_labels(pref: dict):
    hard_preferences = list(dict.fromkeys(pref.get("hard_preferences") or []))
    soft_preferences = list(dict.fromkeys(pref.get("soft_preferences") or []))

    def set_hard(label: str, enabled: bool):
        if enabled and label not in hard_preferences:
            hard_preferences.append(label)
        if not enabled and label in hard_preferences:
            hard_preferences.remove(label)

    def set_soft(label: str, enabled: bool):
        if enabled and label not in soft_preferences:
            soft_preferences.append(label)
        if not enabled and label in soft_preferences:
            soft_preferences.remove(label)

    set_hard("有养宠经验", not pref.get("allow_novice", True) or pref.get("focus_experience", False))
    set_hard("优先同城或本地领养", pref.get("prefer_local", False))
    set_hard("需稳定住房或自有住房", not pref.get("accept_renting", True))
    set_hard("稳定居住环境", pref.get("require_stable_housing", False) or pref.get("focus_stability", False))
    set_hard("基础经济能力", pref.get("require_financial_capacity", False))
    set_hard("家庭成员同意", pref.get("require_family_agreement", False))

    set_soft("陪伴时间", pref.get("focus_companionship", False))
    set_soft("住房稳定性", pref.get("focus_stability", False))
    set_soft("责任意识", True)
    set_soft("安静家庭", pref.get("prefer_quiet_household", False))
    set_soft("多宠相处经验", pref.get("prefer_multi_pet_experience", False))

    pref["hard_preferences"] = hard_preferences
    pref["soft_preferences"] = soft_preferences
    return pref


def _extract_pet_profile(req: PostCreate | PostUpdate):
    text = " ".join(
        [
            req.title or "",
            req.content or "",
            getattr(req, "pet_breed", "") or "",
            getattr(req, "adopt_reason", "") or "",
            getattr(req, "location", "") or "",
        ]
    )

    tag_rules = [
        ("粘人", ["粘人", "亲人", "爱撒娇", "喜欢陪", "跟人"]),
        ("温顺", ["温顺", "乖巧", "懂事", "脾气好"]),
        ("活泼", ["活泼", "好动", "精力旺盛"]),
        ("聪明", ["聪明", "机灵", "听得懂", "边牧", "智商高"]),
        ("独立", ["独立", "不太粘人", "能自己待着"]),
        ("安静", ["安静", "安稳", "不吵", "安静陪伴"]),
        ("胆小", ["胆小", "慢热", "怕生", "敏感"]),
        ("会抓老鼠", ["抓老鼠", "逮老鼠"]),
        ("已绝育", ["绝育", "已绝育"]),
    ]
    tags = [label for label, keywords in tag_rules if any(word in text for word in keywords)]
    if not tags:
        tags = ["亲人", "待了解"]

    pref = _normalize_adoption_preferences(getattr(req, "adoption_preferences", None))
    if any(word in text for word in ["有经验优先", "养宠经验", "不适合新手", "谢绝新手"]):
        pref["allow_novice"] = False
        pref["focus_experience"] = True
    if any(word in text for word in ["仅限同城", "限同城", "本地优先", "仅限本地", "限自提"]):
        pref["prefer_local"] = True
    if any(word in text for word in ["不接受租房", "谢绝租房", "仅限自有住房"]):
        pref["accept_renting"] = False
        pref["require_stable_housing"] = True
    if any(word in text for word in ["稳定住房", "稳定居住", "不要频繁搬家", "长期稳定"]):
        pref["require_stable_housing"] = True
    if any(word in text for word in ["经济能力", "基础预算", "看病预算", "能承担医疗", "有稳定收入"]):
        pref["require_financial_capacity"] = True
    if any(word in text for word in ["家人同意", "全家同意", "室友同意"]):
        pref["require_family_agreement"] = True
    if any(word in text for word in ["粘人", "分离焦虑", "需要陪伴", "陪陪它", "不适合长期独处"]):
        pref["focus_companionship"] = True
    if any(word in text for word in ["稳定工作", "稳定住所", "不要搬家", "长期负责"]):
        pref["focus_stability"] = True
    if any(word in text for word in ["安静家庭", "环境安静", "不要太吵", "怕吵"]):
        pref["prefer_quiet_household"] = True
    if any(word in text for word in ["有猫相处经验", "有狗相处经验", "多宠家庭经验", "原住民相处经验"]):
        pref["prefer_multi_pet_experience"] = True
    if any(word in text for word in ["要求高", "慎重领养", "宁缺毋滥", "严格筛选"]):
        pref["risk_tolerance"] = "conservative"
    elif any(word in text for word in ["条件合适即可", "真心对它好即可", "要求不高", "有爱心即可"]):
        pref["risk_tolerance"] = "relaxed"
    pref = _sync_preference_labels(pref)

    age_text = getattr(req, "pet_age", "") or ""
    age_match = re.search(r"(\d+)", age_text)
    age_value = int(age_match.group(1)) if age_match else 1

    pet_breed = getattr(req, "pet_breed", None) or ""
    species = pet_breed.strip() or ("猫咪" if "猫" in text else "狗狗" if "狗" in text or "犬" in text else "异宠")

    pet_name = getattr(req, "pet_name", None) or "待命名宠物"
    description_parts = []
    if req.content:
        description_parts.append(req.content.strip())
    adopt_reason = getattr(req, "adopt_reason", "") or ""
    if adopt_reason:
        description_parts.append(f"送养原因：{adopt_reason.strip()}")
    description = " ".join(part for part in description_parts if part).strip() or "等待补充详细描述"

    return {
        "name": pet_name,
        "species": species,
        "age": age_value,
        "description": description[:500],
        "tags": ",".join(tags[:6]),
        "adoption_preferences": json.dumps(pref, ensure_ascii=False),
    }


def _sync_adoption_post_pet(cursor, post_id: int, req: PostCreate | PostUpdate, user_id: int):
    profile = _extract_pet_profile(req)
    image_url = getattr(req, "image_url", None) or ""
    cursor.execute("SELECT id FROM pets WHERE source_post_id=?", (post_id,))
    pet = cursor.fetchone()
    if pet:
        cursor.execute(
            """
            UPDATE pets SET
                owner_id=?,
                owner_type='personal',
                name=?,
                species=?,
                age=?,
                description=?,
                image_url=CASE WHEN ? != '' THEN ? ELSE image_url END,
                adoption_preferences=?,
                tags=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE source_post_id=?
            """,
            (
                user_id,
                profile["name"],
                profile["species"],
                profile["age"],
                profile["description"],
                image_url,
                image_url,
                profile["adoption_preferences"],
                profile["tags"],
                post_id,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO pets
            (owner_id, source_post_id, owner_type, name, species, age, description, image_url, adoption_preferences, tags, status)
            VALUES (?, ?, 'personal', ?, ?, ?, ?, ?, ?, ?, '待领养')
            """,
            (
                user_id,
                post_id,
                profile["name"],
                profile["species"],
                profile["age"],
                profile["description"],
                image_url,
                profile["adoption_preferences"],
                profile["tags"],
            ),
        )
    return profile


@router.get("/posts")
def get_posts(skip: int = 0, limit: int = 20):
    if limit > 100:
        limit = 100
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        _ensure_demo_posts(cursor)
        conn.commit()
        cursor.execute(
            """
            SELECT p.id, p.user_id, p.title, p.content, p.image_url,
                   p.image_urls, p.type, p.likes, p.create_time,
                   p.pet_name, p.pet_gender, p.pet_age, p.pet_breed, p.adopt_reason, p.location,
                   pet.adoption_preferences,
                   u.username, u.role,
                   COALESCE(cc.comment_count, 0) AS comment_count
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN pets pet ON pet.source_post_id = p.id
            LEFT JOIN (
                SELECT post_id, COUNT(*) AS comment_count
                FROM comments
                GROUP BY post_id
            ) cc ON cc.post_id = p.id
            ORDER BY p.create_time DESC
            LIMIT ? OFFSET ?
            """,
            (limit, skip),
        )
        items = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) FROM posts")
        total = cursor.fetchone()[0]
    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.post("/posts")
async def publish_post(req: PostCreate, current_user: dict = Depends(get_current_user)):
    if current_user["id"] != req.user_id:
        raise HTTPException(status_code=403, detail="无权限以他人身份发帖")
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO posts
               (user_id, title, content, image_url, image_urls, type,
                pet_name, pet_gender, pet_age, pet_breed, adopt_reason, location)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (req.user_id, req.title, req.content, req.image_url, req.image_urls,
             req.type, req.pet_name, req.pet_gender, req.pet_age,
             req.pet_breed, req.adopt_reason, req.location),
        )
        post_id = cursor.lastrowid
        extracted_profile = None
        if req.type == "adopt_help":
            extracted_profile = _sync_adoption_post_pet(cursor, post_id, req, current_user["id"])
        conn.commit()
    return {"status": "success", "post_id": post_id, "extracted_profile": extracted_profile}


@router.put("/posts/{post_id}")
async def update_post(post_id: int, req: PostUpdate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id=?", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if post["user_id"] != current_user["id"] and current_user.get("role") not in ["org_admin"]:
            raise HTTPException(status_code=403, detail="无权限修改他人帖子")
        cursor.execute(
            """UPDATE posts SET
               title=COALESCE(?,title), content=COALESCE(?,content),
               image_url=COALESCE(?,image_url), image_urls=COALESCE(?,image_urls),
               pet_name=COALESCE(?,pet_name), pet_gender=COALESCE(?,pet_gender),
               pet_age=COALESCE(?,pet_age), pet_breed=COALESCE(?,pet_breed),
               adopt_reason=COALESCE(?,adopt_reason), location=COALESCE(?,location)
               WHERE id=?""",
            (req.title, req.content, req.image_url, req.image_urls,
             req.pet_name, req.pet_gender, req.pet_age, req.pet_breed,
             req.adopt_reason, req.location, post_id),
        )
        merged = dict(post)
        for key in ["title", "content", "image_url", "image_urls", "pet_name", "pet_gender", "pet_age", "pet_breed", "adopt_reason", "location", "adoption_preferences"]:
            new_val = getattr(req, key, None)
            if new_val is not None:
                merged[key] = new_val
        extracted_profile = None
        if merged.get("type") == "adopt_help":
            merged_req = PostCreate(
                user_id=merged["user_id"],
                title=merged.get("title"),
                content=merged.get("content") or "",
                type=merged.get("type") or "adopt_help",
                image_url=merged.get("image_url"),
                image_urls=merged.get("image_urls"),
                pet_name=merged.get("pet_name"),
                pet_gender=merged.get("pet_gender"),
                pet_age=merged.get("pet_age"),
                pet_breed=merged.get("pet_breed"),
                adopt_reason=merged.get("adopt_reason"),
                location=merged.get("location"),
                adoption_preferences=merged.get("adoption_preferences"),
            )
            extracted_profile = _sync_adoption_post_pet(cursor, post_id, merged_req, current_user["id"])
        conn.commit()
    return {"status": "success", "extracted_profile": extracted_profile}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM posts WHERE id=?", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if post["user_id"] != current_user["id"] and current_user.get("role") not in ["org_admin"]:
            raise HTTPException(status_code=403, detail="无权限删除他人帖子")
        cursor.execute("DELETE FROM pets WHERE source_post_id = ?", (post_id,))
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        cursor.execute(
            "INSERT INTO moderation_logs (target_id, admin_id, reason, evidence_url) VALUES (?, ?, ?, ?)",
            (post_id, current_user["id"], "用户删除帖子", ""),
        )
        conn.commit()
    return {"status": "success"}


@router.post("/posts/{post_id}/like")
async def like_post(post_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE posts SET likes = COALESCE(likes,0) + 1 WHERE id = ?", (post_id,))
        conn.commit()
    return {"status": "success"}


@router.post("/posts/comment")
async def create_comment(req: CommentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["id"] != req.user_id:
        raise HTTPException(status_code=403, detail="无权限以他人身份评论")
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
            (req.post_id, req.user_id, req.content),
        )
        conn.commit()
    return {"status": "success"}


@router.get("/posts/{post_id}/comments")
def get_comments(post_id: int):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT c.*, u.username FROM comments c JOIN users u ON c.user_id = u.id WHERE post_id = ? ORDER BY c.create_time ASC",
            (post_id,),
        )
        res = [dict(row) for row in cursor.fetchall()]
    return res
