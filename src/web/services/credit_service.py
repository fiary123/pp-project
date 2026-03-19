import json
from datetime import datetime
from typing import Dict, Optional
import sqlite3
from src.database.db_config import SQLITE_DB_PATH

class CreditService:
    def __init__(self, llm_service):
        self.llm = llm_service
        self.db_path = SQLITE_DB_PATH

    async def add_credit_event(self, user_id: int, event_type: str, content: str = ""):
        """
        核心方法：处理信用事件
        event_type: 'visit_report', 'course_done', 'help_others', 'pet_return'
        """
        # 1. 基础配置映射
        config = {
            "visit_report": {"base": 10, "dim": "responsibility_score"},
            "course_done":  {"base": 20, "dim": "engagement_score"},
            "help_others":  {"base": 5,  "dim": "community_score"},
            "pet_return":   {"base": -100, "dim": "responsibility_score"}
        }.get(event_type)

        if not config: return

        # 2. AI 质量分析 (针对有文字内容的事件)
        multiplier = 1.0
        if event_type == "visit_report" and content:
            multiplier = await self._get_ai_quality_multiplier(content)
        
        final_points = config["base"] * multiplier

        # 3. 写入数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # 记录明细
            cursor.execute('''
                INSERT INTO credit_events 
                (user_id, event_type, dimension, content, base_points, llm_multiplier, final_points)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, event_type, config["dim"].replace("_score",""), content, config["base"], multiplier, final_points))

            # 更新画像总分
            cursor.execute(f'''
                UPDATE user_credit_profiles 
                SET {config["dim"]} = {config["dim"]} + ?
                WHERE user_id = ?
            ''', (final_points, user_id))
            
            # 如果是新用户，初始化档案
            if cursor.rowcount == 0:
                cursor.execute(f'''
                    INSERT INTO user_credit_profiles (user_id, {config["dim"]})
                    VALUES (?, ?)
                ''', (user_id, 100.0 + final_points if "responsibility" in config["dim"] else final_points))

            # 4. 等级晋升逻辑
            self._update_user_level(cursor, user_id)
            
            conn.commit()
            return {"points": final_points, "multiplier": multiplier}
        finally:
            conn.close()

    async def _get_ai_quality_multiplier(self, content: str) -> float:
        """调用 LLM 评估回访内容质量"""
        prompt = f"""
        你是一个宠物领养回访质量评估专家。请分析以下回访内容，判断其真实性和详尽程度。
        内容: "{content}"
        
        评分要求：
        - 如果内容包含宠物饮食、排泄、精神状态的细节描述，系数给 0.8-1.0。
        - 如果内容只有敷衍的几个字（如“还行”、“没死”），系数给 0.1-0.3。
        - 仅返回一个 0.1 到 1.0 之间的数字。
        """
        try:
            res = await self.llm.ask(prompt)
            return float(res.strip())
        except:
            return 0.5

    def _update_user_level(self, cursor, user_id):
        """根据总分更新等级 (Bronze -> Silver -> Gold -> Black)"""
        cursor.execute("SELECT responsibility_score + engagement_score + community_score FROM user_credit_profiles WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        
        level = "Bronze"
        if total >= 500: level = "Black"
        elif total >= 300: level = "Gold"
        elif total >= 150: level = "Silver"
        
        cursor.execute("UPDATE user_credit_profiles SET level = ? WHERE user_id = ?", (level, user_id))

    def get_user_credit(self, user_id: int):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_credit_profiles WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return dict(res) if res else None
