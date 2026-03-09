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
