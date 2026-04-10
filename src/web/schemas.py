from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    code: str # 验证码

class SendCodeRequest(BaseModel):
    email: str

class PostCreate(BaseModel):
    user_id: int
    title: Optional[str] = None
    content: str
    type: str = "daily"
    image_url: Optional[str] = None          # 兼容旧字段（单图）
    image_urls: Optional[str] = None         # 多图，JSON 数组字符串
    # 送养帖专属字段
    pet_name: Optional[str] = None
    pet_gender: Optional[str] = None         # male / female / unknown
    pet_age: Optional[str] = None            # 如 "2岁3个月"
    pet_breed: Optional[str] = None          # 品种
    adopt_reason: Optional[str] = None       # 送养原因
    location: Optional[str] = None           # 所在地址
    adoption_preferences: Optional[dict] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: Optional[str] = None
    pet_name: Optional[str] = None
    pet_gender: Optional[str] = None
    pet_age: Optional[str] = None
    pet_breed: Optional[str] = None
    adopt_reason: Optional[str] = None
    location: Optional[str] = None
    adoption_preferences: Optional[dict] = None

class CommentCreate(BaseModel):
    post_id: int
    user_id: int
    content: str

class PetUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    adoption_preferences: Optional[str] = None

class PetBatchItem(BaseModel):
    name: str
    species: str = "猫"
    age: int = 1
    gender: str = "unknown"          # male / female / unknown
    description: Optional[str] = None
    image_url: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[str] = "[]"

class PetBatchCreate(BaseModel):
    owner_id: int
    pets: List[PetBatchItem]

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
    # 追问答案（第二轮对话时由前端传入，key 对应 generate_followup_questions 返回的 key 字段）
    followup_answers: Optional[dict] = None
    # 目标宠物信息（用户点击"申请领养"时传入）
    target_pet_name: Optional[str] = None
    target_species: Optional[str] = None

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
    code: str # 增加验证码必填

class ApplicationUpdateRequest(BaseModel):
    app_id: int
    status: str


class AdoptionApplicationCreateRequest(BaseModel):
    pet_id: int
    apply_reason: str = Field(min_length=5, description="申请理由")
    ai_decision: Optional[str] = Field(default=None, description="AI 辅助结论")
    ai_readiness_score: Optional[float] = Field(default=None, description="AI 准备度评分")
    ai_summary: Optional[str] = Field(default="", description="AI 评估摘要")
    risk_level: Optional[str] = Field(default="Medium", description="风险等级")
    consensus_score: Optional[float] = Field(default=None, description="专家共识分数")
    missing_fields: List[str] = Field(default_factory=list, description="仍缺失的关键信息")
    conflict_notes: List[str] = Field(default_factory=list, description="专家冲突说明")
    followup_questions: List[str] = Field(default_factory=list, description="建议继续追问的问题")
    memory_scope: Optional[str] = Field(default="", description="记忆作用域")
    assessment_payload: Optional[dict] = Field(default=None, description="用于后续 Flow 继续运行的完整评估输入")


class OwnerApplicationDecisionRequest(BaseModel):
    status: Literal["approved", "rejected", "probing", "human_review"]
    owner_note: str = Field(default="", description="送养方备注或追问内容")

class UserSanctionRequest(BaseModel):
    user_id: int
    admin_id: int
    type: Literal["muted", "banned"]
    reason: str
    evidence: Optional[str] = ""

class SmartMatchRequest(BaseModel):
    user_query: str
    pet_list: List[dict] = Field(default_factory=list)
    followup_answers: Optional[dict] = Field(default=None, description="追问答案字典，key为偏好维度，value为用户选择")


class MatchFollowupRequest(BaseModel):
    user_query: str


class AdoptionFeedbackRequest(BaseModel):
    user_id: int
    pet_id: int
    pet_name: str
    overall_satisfaction: int = Field(ge=1, le=5, description="整体满意度 1-5")
    bond_level: Literal["very_close", "close", "normal", "distant"] = Field(description="与宠物的亲密程度")
    unexpected_challenges: str = Field(default="", description="遇到的意外挑战")
    would_recommend: bool = Field(description="是否向他人推荐领养")
    free_feedback: str = Field(default="", description="自由反馈文本")


class AdoptionEvaluationFollowupRequest(BaseModel):
    supplement_text: str = Field(default="", description="申请人补充的自由文本")
    applicant_info: Optional[str] = Field(default=None, description="更新后的申请人情况描述")
    application_reason: Optional[str] = Field(default=None, description="更新后的申请理由")
    monthly_budget: Optional[float] = Field(default=None, ge=0, description="更新后的月预算")
    daily_companion_hours: Optional[float] = Field(default=None, ge=0, le=24, description="更新后的日陪伴时长")
    has_pet_experience: Optional[bool] = Field(default=None, description="是否有养宠经验")
    housing_type: Optional[Literal["apartment", "house", "other"]] = Field(default=None, description="住房类型")
    existing_pets: Optional[str] = Field(default=None, description="原住宠物情况")


class AdoptionEvaluationReviewRequest(BaseModel):
    status: Literal["approved", "rejected", "probing", "human_review"]
    note: str = Field(default="", description="发布者或管理员的审核备注")


class AdoptionEvaluationFeedbackRequest(BaseModel):
    overall_satisfaction: int = Field(ge=1, le=5, description="整体满意度 1-5")
    bond_level: Literal["very_close", "close", "normal", "distant"] = Field(description="与宠物的亲密程度")
    unexpected_challenges: str = Field(default="", description="遇到的意外挑战")
    would_recommend: bool = Field(description="是否向他人推荐领养")
    free_feedback: str = Field(default="", description="自由反馈文本")

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
    publisher_preferences: Optional[dict] = Field(default=None, description="送养方结构化偏好设置")


class PetChatRequest(BaseModel):
    pet_name: str
    pet_species: str
    pet_desc: str = ""
    user_msg: str
    user_id: Optional[int] = None


class AdoptionRiskFactor(BaseModel):
    """单条风险因子"""
    dimension: str = Field(description="风险维度，如：经济、时间、经验、住房、动机")
    description: str = Field(description="风险描述")
    severity: Literal["low", "medium", "high"] = Field(description="严重程度")


class AdoptionAssessmentDimension(BaseModel):
    """七维领养评估结果"""
    key: str = Field(description="维度编码")
    label: str = Field(description="维度名称")
    score: int = Field(ge=0, le=100, description="维度评分 0-100")
    risk_level: Literal["Low", "Medium", "High"] = Field(description="维度风险等级")
    evidence: List[str] = Field(default_factory=list, description="当前维度的判断依据")
    missing_info: List[str] = Field(default_factory=list, description="当前维度仍缺失的信息")
    suggestion: str = Field(default="", description="该维度的优化建议")


class MutualAidTaskCreate(BaseModel):
    user_id: Optional[int] = None
    task_type: str = "上门喂养"
    pet_name: str
    pet_species: str = "猫"
    start_time: str
    end_time: Optional[str] = None
    location: str
    description: Optional[str] = None

class MutualAidMatchRequest(BaseModel):
    query: str
    user_id: Optional[int] = None

class MutualAidAcceptRequest(BaseModel):
    helper_id: Optional[int] = None

class MutualAidReportRequest(BaseModel):
    reporter_id: Optional[int] = None
    reason: str


class TakedownRequest(BaseModel):
    reason: str
    admin_id: Optional[int] = None
    evidence_url: Optional[str] = ""

class NotificationReadRequest(BaseModel):
    notification_id: int
