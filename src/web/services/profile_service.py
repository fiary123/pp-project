import sqlite3
from src.web.services.db_service import get_db
from src.web.schemas import UserProfileUpdate, UserPreferenceUpdate, PetFeatureUpdate, PetRequirementUpdate
from typing import Optional

class ProfileService:
    @staticmethod
    def get_user_profile(user_id: int):
        """获取用户画像基础信息"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_user_profile(user_id: int, profile: UserProfileUpdate):
        """更新用户画像信息 (不存在则创建)"""
        with get_db() as conn:
            cursor = conn.cursor()
            # 确保记录存在
            cursor.execute("INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (user_id,))
            
            fields = profile.dict(exclude_unset=True)
            if fields:
                set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
                values = list(fields.values()) + [user_id]
                cursor.execute(f"UPDATE user_profiles SET {set_clause}, update_time = CURRENT_TIMESTAMP WHERE user_id = ?", values)
            
            conn.commit()
            return True

    @staticmethod
    def get_user_preferences(user_id: int):
        """获取用户领养偏好"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_user_preferences(user_id: int, preferences: UserPreferenceUpdate):
        """更新用户领养偏好 (不存在则创建)"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO user_preferences (user_id) VALUES (?)", (user_id,))
            
            fields = preferences.dict(exclude_unset=True)
            if fields:
                set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
                values = list(fields.values()) + [user_id]
                cursor.execute(f"UPDATE user_preferences SET {set_clause}, update_time = CURRENT_TIMESTAMP WHERE user_id = ?", values)
            
            conn.commit()
            return True

    @staticmethod
    def get_pet_features(pet_id: int):
        """获取宠物推荐特征"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pet_features WHERE pet_id = ?", (pet_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_pet_features(pet_id: int, features: PetFeatureUpdate):
        """更新宠物推荐特征 (不存在则创建)"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO pet_features (pet_id) VALUES (?)", (pet_id,))
            
            fields = features.dict(exclude_unset=True)
            if fields:
                set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
                values = list(fields.values()) + [pet_id]
                cursor.execute(f"UPDATE pet_features SET {set_clause}, update_time = CURRENT_TIMESTAMP WHERE pet_id = ?", values)
            
            conn.commit()
            return True

    @staticmethod
    def get_pet_requirements(pet_id: int):
        """获取发布者的领养要求"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pet_requirements WHERE pet_id = ?", (pet_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_pet_requirements(pet_id: int, requirements: PetRequirementUpdate):
        """更新发布者的领养要求 (不存在则创建)"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO pet_requirements (pet_id) VALUES (?)", (pet_id,))
            
            fields = requirements.dict(exclude_unset=True)
            if fields:
                set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
                values = list(fields.values()) + [pet_id]
                cursor.execute(f"UPDATE pet_requirements SET {set_clause}, update_time = CURRENT_TIMESTAMP WHERE pet_id = ?", values)
            
            conn.commit()
            return True
