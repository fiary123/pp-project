from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Literal["individual", "org_admin", "root"] = "individual"

class PostCreate(BaseModel):
    user_id: int
    title: Optional[str] = None
    content: str
    type: str = "daily"
    image_url: Optional[str] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None

class CommentCreate(BaseModel):
    post_id: int
    user_id: int
    content: str

class PetUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    is_hot: Optional[int] = 0

class NutritionPlanRequest(BaseModel):
    user_id: int
    pet_name: str
    species: Literal["cat", "dog"]
    age_months: int = Field(ge=0, le=400)
    weight_kg: float = Field(gt=0, le=150)
    neutered: bool = False
    activity_level: Literal["low", "medium", "high"] = "medium"
    goal: Literal["maintain", "lose_weight", "gain_weight"] = "maintain"
    food_kcal_per_100g: float = Field(default=360, gt=0, le=900)
    symptoms: List[str] = Field(default_factory=list)

class NutritionFeedbackRequest(BaseModel):
    plan_id: int
    weight_change: Literal["gain", "lose", "stable"]
    appetite_status: Literal["good", "normal", "poor"]
    stool_status: Literal["normal", "soft", "hard", "diarrhea"]
    activity_change: Literal["increase", "stable", "decrease"]

class NutritionReplanRequest(BaseModel):
    plan_id: int
    feedback_id: int

class ChatRequest(BaseModel):
    message: str

class TriageRequest(BaseModel):
    symptom: str
    location: Optional[str] = None

class MessageCreate(BaseModel):
    sender_id: int
    receiver_id: int
    content: str

class ChangePasswordRequest(BaseModel):
    user_id: int
    old_password: str
    new_password: str

class ApplicationUpdateRequest(BaseModel):
    app_id: int
    status: str

class UserSanctionRequest(BaseModel):
    user_id: int
    admin_id: int
    type: Literal["muted", "banned"]
    reason: str
    evidence: Optional[str] = ""

class SmartMatchRequest(BaseModel):
    user_query: str
    pet_list: List[dict] = Field(default_factory=list)

class AdoptionAssessmentRequest(BaseModel):
    """领养资质评估请求 - 输入层"""
    # 申请人画像信息
    applicant_info: str = Field(min_length=10, description="申请人的个人情况描述（居住环境、职业、作息等）")
    application_reason: str = Field(default="", description="领养申请理由（自由文本，用于语义动机分析）")
    # 宠物信息
    target_species: Literal["cat", "dog"] = Field(description="目标宠物物种")
    target_pet_name: str = Field(min_length=1, description="目标宠物名称")
    # 量化条件
    monthly_budget: float = Field(default=0, ge=0, description="申请人月均养宠预算（元），0表示未填写")
    daily_companion_hours: float = Field(default=0, ge=0, le=24, description="工作日每天可陪伴宠物的时长（小时）")
    has_pet_experience: bool = Field(default=False, description="是否有养宠经验")
    housing_type: Literal["apartment", "house", "other"] = Field(default="apartment", description="住房类型")
    # 原住宠物
    existing_pets: str = Field(default="", description="家中原住宠物情况，无则留空")


class AdoptionRiskFactor(BaseModel):
    """单条风险因子"""
    dimension: str = Field(description="风险维度，如：经济、时间、经验、住房、动机")
    description: str = Field(description="风险描述")
    severity: Literal["low", "medium", "high"] = Field(description="严重程度")


class AdoptionAssessmentResponse(BaseModel):
    """领养资质评估响应 - 符合需求文档的完整结构化输出"""
    # 核心评分
    readiness_score: int = Field(ge=0, le=100, description="领养准备度评分 0-100")
    success_probability: float = Field(ge=0.0, le=1.0, description="稳定领养成功倾向 0-1")
    confidence_level: float = Field(ge=0.0, le=1.0, description="AI 评估置信度 0-1")
    # 决策结论
    risk_level: Literal["Low", "Medium", "High"] = Field(description="综合风险等级")
    decision: Literal["pass", "conditional_pass", "review_required", "reject"] = Field(
        description="系统建议决策：pass=建议通过 / conditional_pass=条件通过 / review_required=人工复核 / reject=建议驳回"
    )
    need_manual_review: bool = Field(description="是否需要人工二次核验")
    # 详细分析
    risk_factors: List[AdoptionRiskFactor] = Field(default_factory=list, description="风险因子列表")
    recommendations: List[str] = Field(default_factory=list, description="个性化建议与补救策略")
    review_note: str = Field(default="", description="给管理员的审核备注")
    # 子报告
    baseline_report: str = Field(description="品种养护基准报告")
    profile_report: str = Field(description="申请人画像匹配报告")
    cohabitation_report: str = Field(description="共处环境风险报告")
    final_summary: str = Field(description="三专家综合摘要（Markdown）")
    # 追踪
    trace_id: str = Field(description="AI 执行链路 trace_id，可在管理后台溯源")
