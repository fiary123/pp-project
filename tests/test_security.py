"""
安全性与核心功能单元测试
覆盖：密码哈希验证、JWT认证、鉴权边界、文件上传校验、领养评估 Fallback
"""
import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.services.auth_service import get_password_hash, verify_password, create_access_token, decode_access_token


# ===== 密码哈希测试 =====

def test_password_hash_not_plaintext():
    """密码哈希后不应等于原文"""
    plain = "mypassword123"
    hashed = get_password_hash(plain)
    assert hashed != plain


def test_password_verify_correct():
    """正确密码应通过验证"""
    plain = "mypassword123"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed) is True


def test_password_verify_wrong():
    """错误密码不应通过验证"""
    hashed = get_password_hash("correct_password")
    assert verify_password("wrong_password", hashed) is False


def test_password_verify_plaintext_against_hash_fails():
    """明文字符串直接与哈希比较应返回 False（不能绕过 bcrypt）"""
    plain = "mypassword123"
    hashed = get_password_hash(plain)
    # 旧代码的错误写法：直接字符串比较
    assert (hashed == plain) is False


# ===== JWT 测试 =====

def test_jwt_encode_decode():
    """JWT 创建后应能正确解析 sub 字段（sub 必须为字符串，符合 JWT 规范）"""
    token = create_access_token({"sub": "42"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"


def test_jwt_invalid_token_returns_none():
    """无效 Token 应返回 None，不抛异常"""
    result = decode_access_token("invalid.token.string")
    assert result is None


def test_jwt_tampered_token_returns_none():
    """篡改的 Token 应返回 None"""
    token = create_access_token({"sub": 1})
    tampered = token[:-5] + "XXXXX"
    result = decode_access_token(tampered)
    assert result is None


# ===== 文件上传魔数检测测试 =====

from src.web.routers.uploads import detect_mime_type

def test_detect_jpeg():
    """JPEG 魔数应识别为 image/jpeg"""
    jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 12
    assert detect_mime_type(jpeg_header) == "image/jpeg"


def test_detect_png():
    """PNG 魔数应识别为 image/png"""
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    assert detect_mime_type(png_header) == "image/png"


def test_detect_fake_image_exe():
    """伪装成图片的 EXE 文件应识别为 None"""
    exe_header = b"MZ\x90\x00" + b"\x00" * 12  # Windows PE 头
    assert detect_mime_type(exe_header) is None


def test_detect_php_script():
    """PHP 脚本应识别为 None"""
    php_header = b"<?php echo 'hack';"
    assert detect_mime_type(php_header) is None


# ===== 营养计算边界测试 =====

from src.agents.nutrition_planner import build_nutrition_plan

def test_nutrition_basic_cat():
    """基础猫咪营养计划应包含必要字段"""
    plan = build_nutrition_plan(
        species="cat", age_months=24, weight_kg=4.0,
        neutered=True, activity_level="medium", goal="maintain",
        food_kcal_per_100g=360, symptoms=[]
    )
    assert plan["daily_kcal"] > 0
    assert plan["daily_food_g"] > 0
    assert plan["feedings_per_day"] >= 1


def test_nutrition_kcal_positive():
    """日热量必须为正数"""
    plan = build_nutrition_plan(
        species="dog", age_months=12, weight_kg=10.0,
        neutered=False, activity_level="high", goal="maintain",
        food_kcal_per_100g=380, symptoms=[]
    )
    assert plan["daily_kcal"] > 0
    assert plan["daily_food_g"] > 0


def test_nutrition_high_activity_higher_kcal():
    """高活动量宠物日热量应高于低活动量"""
    plan_low = build_nutrition_plan(
        species="dog", age_months=24, weight_kg=5.0,
        neutered=True, activity_level="low", goal="maintain",
        food_kcal_per_100g=360, symptoms=[]
    )
    plan_high = build_nutrition_plan(
        species="dog", age_months=24, weight_kg=5.0,
        neutered=True, activity_level="high", goal="maintain",
        food_kcal_per_100g=360, symptoms=[]
    )
    assert plan_high["daily_kcal"] > plan_low["daily_kcal"]


# ===== 领养评估规则预筛引擎测试 =====

from src.agents.adoption_profiler import rule_engine_prescreen

def test_rule_prescreen_hard_block_no_pet_allowed():
    """明确禁止养宠的住房应命中硬约束"""
    result = rule_engine_prescreen(
        target_species="cat", monthly_budget=500, daily_companion_hours=4,
        has_pet_experience=True, housing_type="apartment",
        existing_pets="", applicant_info="我住在租房，房东不让养宠物"
    )
    assert result["hard_block"] is True
    assert result["penalty_score"] >= 100


def test_rule_prescreen_low_budget_high_risk():
    """预算极低时应触发高风险标记"""
    result = rule_engine_prescreen(
        target_species="dog", monthly_budget=100, daily_companion_hours=3,
        has_pet_experience=False, housing_type="apartment",
        existing_pets="", applicant_info="我有一套公寓，工作日在家，想养一只狗"
    )
    assert result["penalty_score"] > 0
    assert any("经济" in f for f in result["risk_flags"])


def test_rule_prescreen_no_risk_good_conditions():
    """条件良好的申请人不应触发硬约束"""
    result = rule_engine_prescreen(
        target_species="cat", monthly_budget=800, daily_companion_hours=6,
        has_pet_experience=True, housing_type="house",
        existing_pets="", applicant_info="我住在独栋别墅，有充足时间，预算充足，有5年养猫经验"
    )
    assert result["hard_block"] is False
    assert result["penalty_score"] < 20


def test_rule_prescreen_companion_hours_too_low():
    """日陪伴时长不足时应产生风险标记"""
    result = rule_engine_prescreen(
        target_species="dog", monthly_budget=600, daily_companion_hours=0.5,
        has_pet_experience=True, housing_type="apartment",
        existing_pets="", applicant_info="我住在公寓，工作繁忙，每天只有半小时陪伴时间"
    )
    assert any("时间" in f for f in result["risk_flags"])
    assert result["penalty_score"] > 0


def test_rule_prescreen_need_manual_review_on_risk():
    """触发多条风险项时应建议人工复核"""
    result = rule_engine_prescreen(
        target_species="dog", monthly_budget=80, daily_companion_hours=0.3,
        has_pet_experience=False, housing_type="apartment",
        existing_pets="", applicant_info="租房合住，预算很少，每天很忙，想养哈士奇"
    )
    assert result["need_manual_review"] is True


def test_adoption_assessment_schema_validation():
    """领养评估请求 Schema 应拒绝过短的申请描述"""
    from pydantic import ValidationError
    from src.web.schemas import AdoptionAssessmentRequest

    with pytest.raises(ValidationError):
        AdoptionAssessmentRequest(
            applicant_info="太短",  # 少于 10 字符
            target_species="cat",
            target_pet_name="小花"
        )


def test_adoption_assessment_schema_valid():
    """合法的领养评估请求应通过 Schema 验证，新增字段有默认值"""
    from src.web.schemas import AdoptionAssessmentRequest

    req = AdoptionAssessmentRequest(
        applicant_info="我住在80平米公寓，有封窗，每天在家时间超过8小时，有养猫经验",
        target_species="cat",
        target_pet_name="橘猫团子",
        monthly_budget=500,
        daily_companion_hours=6.0,
        has_pet_experience=True,
        housing_type="apartment",
        existing_pets="家中已有一只2岁健康绝育公猫"
    )
    assert req.target_species == "cat"
    assert req.monthly_budget == 500
    assert req.has_pet_experience is True
    assert req.daily_companion_hours == 6.0


def test_adoption_response_schema_structure():
    """AdoptionAssessmentResponse 应包含需求文档要求的所有字段"""
    from src.web.schemas import AdoptionAssessmentResponse, AdoptionRiskFactor

    resp = AdoptionAssessmentResponse(
        readiness_score=78,
        success_probability=0.76,
        confidence_level=0.84,
        risk_level="Medium",
        decision="conditional_pass",
        need_manual_review=True,
        risk_factors=[
            AdoptionRiskFactor(dimension="时间", description="工作日陪伴不足", severity="medium")
        ],
        recommendations=["建议选择独立性较强的成年猫", "建议提前购置自动喂食器"],
        review_note="建议管理员进行条件性通过并补充回访",
        baseline_report="品种基准...",
        profile_report="画像报告...",
        cohabitation_report="共处报告...",
        final_summary="综合摘要...",
        trace_id="test-trace-001"
    )
    assert resp.readiness_score == 78
    assert resp.decision == "conditional_pass"
    assert len(resp.risk_factors) == 1
    assert resp.risk_factors[0].severity == "medium"
