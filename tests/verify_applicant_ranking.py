import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.web.services.db_service import get_db, ensure_tables
from src.web.services.profile_service import ProfileService
from src.web.services.pet_service import PetService
from src.web.services.application_service import ApplicationService
from src.web.services.recommendation_service import RecommendationService
from src.web.schemas import UserProfileUpdate, UserPreferenceUpdate, PetFeatureUpdate, PetRequirementUpdate

async def verify_applicant_ranking():
    print("开始验证申请人排序流水线...")
    
    # 1. 确保表结构最新
    with get_db() as conn:
        ensure_tables(conn)
    
    # 2. 准备测试数据
    # 我们假设: 
    # 用户 1 是发布者
    # 用户 2 是申请人 A (完美匹配)
    # 用户 3 是申请人 B (有风险：租房且无经验)
    # 宠物 1 是待领养宠物
    
    publisher_id = 1
    applicant_perfect_id = 2
    applicant_risky_id = 3
    test_pet_id = 1
    
    profile_service = ProfileService()
    
    # 设置宠物要求：需要经验，要求稳定住房，要求回访
    print("设置宠物要求...")
    profile_service.update_pet_requirements(test_pet_id, PetRequirementUpdate(
        require_experience="1-3年",
        require_stable_housing=True,
        require_return_visit=True
    ))
    
    # 设置申请人 A (完美匹配)
    print("设置申请人 A 画像...")
    profile_service.update_user_profile(applicant_perfect_id, UserProfileUpdate(
        housing_type="别墅",
        rental_status="自购",
        pet_experience="3年以上",
        available_time=4.0,
        family_support=True
    ))
    
    # 设置申请人 B (有风险)
    print("设置申请人 B 画像...")
    profile_service.update_user_profile(applicant_risky_id, UserProfileUpdate(
        housing_type="公寓",
        rental_status="租房",
        pet_experience="无",
        available_time=0.5,
        family_support=False
    ))
    
    # 3. 创建申请记录
    print("创建申请记录...")
    with get_db() as conn:
        cursor = conn.cursor()
        # 清除旧数据以便测试
        cursor.execute("DELETE FROM applications WHERE pet_id = ?", (test_pet_id,))
        
        # 申请人 A 接受回访
        cursor.execute(
            "INSERT INTO applications (user_id, pet_id, apply_reason, accept_return_visit, status) VALUES (?, ?, ?, ?, ?)",
            (applicant_perfect_id, test_pet_id, "我很喜欢这只宠物，有丰富经验", 1, "pending")
        )
        # 申请人 B 不接受回访
        cursor.execute(
            "INSERT INTO applications (user_id, pet_id, apply_reason, accept_return_visit, status) VALUES (?, ?, ?, ?, ?)",
            (applicant_risky_id, test_pet_id, "想养只宠物玩玩", 0, "pending")
        )
        conn.commit()

    # 4. 执行排序逻辑
    print("\n执行申请人排序...")
    recommender = RecommendationService(profile_service)
    results = await recommender.rank_applicants_for_pet(test_pet_id)
    
    print(f"\n找到 {len(results)} 个合格候选人 (经过硬性过滤):")
    for i, item in enumerate(results):
        print(f"排名 {i+1}: 用户ID {item.candidate_id}, 总分 {item.final_score:.2f}")
        print(f"  匹配理由: {item.reasons}")
        print(f"  风险提示: {item.risk_flags}")
        print(f"  分项得分: {item.scores}")

    # 5. 断言验证
    if len(results) > 0:
        assert results[0].candidate_id == applicant_perfect_id, "完美匹配的申请人应该排在第一位"
        print("\n验证成功：完美匹配者排在首位。")
    else:
        print("\n错误：未找到候选人。")

if __name__ == "__main__":
    asyncio.run(verify_applicant_ranking())
