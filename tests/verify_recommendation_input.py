import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.web.services.profile_service import ProfileService
from src.web.schemas import (
    UserProfileUpdate, 
    UserPreferenceUpdate, 
    PetFeatureUpdate, 
    PetRequirementUpdate
)
from src.web.services.db_service import get_db, ensure_tables

def verify_input_layer():
    print("开始验证推荐系统输入层...")
    
    # 1. 确保数据库表存在
    with get_db() as conn:
        ensure_tables(conn)
    
    test_user_id = 4  # 使用现有用户 ID
    test_pet_id = 1   # 使用现有宠物 ID
    
    # --- 验证用户画像 ---
    print("\n[1/4] 验证用户画像 (User Profile)...")
    profile_data = UserProfileUpdate(
        housing_type="公寓",
        housing_size=85.5,
        rental_status="自购",
        pet_experience="1-3年",
        available_time=2.5,
        family_support=True,
        budget_level="中"
    )
    ProfileService.update_user_profile(test_user_id, profile_data)
    saved_profile = ProfileService.get_user_profile(test_user_id)
    print(f"保存的数据: {saved_profile}")
    assert saved_profile['housing_type'] == "公寓"
    assert saved_profile['family_support'] == 1
    print("用户画像验证成功!")

    # --- 验证用户偏好 ---
    print("\n[2/4] 验证用户偏好 (User Preference)...")
    pref_data = UserPreferenceUpdate(
        preferred_pet_type="猫",
        preferred_age_range="幼年",
        preferred_size="小型",
        accept_special_care=False,
        accept_high_energy=True
    )
    ProfileService.update_user_preferences(test_user_id, pref_data)
    saved_pref = ProfileService.get_user_preferences(test_user_id)
    print(f"保存的数据: {saved_pref}")
    assert saved_pref['preferred_pet_type'] == "猫"
    assert saved_pref['accept_high_energy'] == 1
    print("用户偏好验证成功!")

    # --- 验证宠物特征 ---
    print("\n[3/4] 验证宠物特征 (Pet Feature)...")
    feature_data = PetFeatureUpdate(
        energy_level="高",
        care_level="中等",
        beginner_friendly=True,
        social_level="友好",
        special_care_flag=False
    )
    ProfileService.update_pet_features(test_pet_id, feature_data)
    saved_feature = ProfileService.get_pet_features(test_pet_id)
    print(f"保存的数据: {saved_feature}")
    assert saved_feature['energy_level'] == "高"
    assert saved_feature['beginner_friendly'] == 1
    print("宠物特征验证成功!")

    # --- 验证宠物要求 ---
    print("\n[4/4] 验证宠物要求 (Pet Requirement)...")
    req_data = PetRequirementUpdate(
        require_experience="无",
        require_stable_housing=True,
        require_return_visit=True,
        region_limit="同城"
    )
    ProfileService.update_pet_requirements(test_pet_id, req_data)
    saved_req = ProfileService.get_pet_requirements(test_pet_id)
    print(f"保存的数据: {saved_req}")
    assert saved_req['region_limit'] == "同城"
    assert saved_req['require_stable_housing'] == 1
    print("宠物要求验证成功!")

    print("\n所有输入层数据模块验证通过!")

if __name__ == "__main__":
    try:
        verify_input_layer()
    except Exception as e:
        print(f"验证失败: {e}")
        sys.exit(1)
