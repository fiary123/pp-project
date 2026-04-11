这一步的目标只有一个：

先把推荐输入层补齐。

也就是先把这四类数据做出来：

用户画像 user_profiles
用户偏好 user_preferences
宠物推荐特征 pet_features
宠物领养要求 pet_requirements

这样你下一步才能正式开始写推荐流水线。

一、建议先新增的文件
app/models/user_profile.py
app/models/user_preference.py
app/models/pet_feature.py
app/models/pet_requirement.py

app/schemas/profile_schema.py
app/schemas/pet_feature_schema.py

app/service/profile_service.py
app/service/pet_feature_service.py

app/router/profile.py
app/router/pet_feature.py

下面代码按常见 FastAPI + SQLAlchemy 结构写。
如果你项目里字段命名风格不一样，可以再统一改。

二、模型层 models
1. app/models/user_profile.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    housing_type = Column(String(50), nullable=True)      # apartment / house / dorm / other
    housing_size = Column(String(50), nullable=True)      # small / medium / large
    rental_status = Column(String(50), nullable=True)     # rent / own / family
    pet_experience = Column(Boolean, default=False)
    available_time = Column(String(50), nullable=True)    # low / medium / high
    family_support = Column(Boolean, default=False)
    budget_level = Column(String(50), nullable=True)      # low / medium / high

    user = relationship("User", back_populates="profile")
2. app/models/user_preference.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    preferred_pet_type = Column(String(50), nullable=True)      # cat / dog / other
    preferred_age_range = Column(String(50), nullable=True)     # child / adult / senior
    preferred_size = Column(String(50), nullable=True)          # small / medium / large
    accept_special_care = Column(Boolean, default=False)
    accept_high_energy = Column(Boolean, default=False)

    user = relationship("User", back_populates="preference")
3. app/models/pet_feature.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class PetFeature(Base):
    __tablename__ = "pet_features"

    id = Column(Integer, primary_key=True, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id", ondelete="CASCADE"), unique=True, nullable=False)

    energy_level = Column(String(50), nullable=True)       # low / medium / high
    care_level = Column(String(50), nullable=True)         # low / medium / high
    beginner_friendly = Column(Boolean, default=True)
    social_level = Column(String(50), nullable=True)       # low / medium / high
    special_care_flag = Column(Boolean, default=False)

    pet = relationship("Pet", back_populates="feature")
4. app/models/pet_requirement.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class PetRequirement(Base):
    __tablename__ = "pet_requirements"

    id = Column(Integer, primary_key=True, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id", ondelete="CASCADE"), unique=True, nullable=False)

    require_experience = Column(Boolean, default=False)
    require_stable_housing = Column(Boolean, default=False)
    require_return_visit = Column(Boolean, default=False)
    region_limit = Column(String(100), nullable=True)

    pet = relationship("Pet", back_populates="requirement")
三、如果你原来的 User / Pet 模型要补关系
User 模型中补：
profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
preference = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
Pet 模型中补：
feature = relationship("PetFeature", back_populates="pet", uselist=False, cascade="all, delete-orphan")
requirement = relationship("PetRequirement", back_populates="pet", uselist=False, cascade="all, delete-orphan")
四、Schema 层
1. app/schemas/profile_schema.py
from pydantic import BaseModel
from typing import Optional


class UserProfileBase(BaseModel):
    housing_type: Optional[str] = None
    housing_size: Optional[str] = None
    rental_status: Optional[str] = None
    pet_experience: bool = False
    available_time: Optional[str] = None
    family_support: bool = False
    budget_level: Optional[str] = None


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileOut(UserProfileBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class UserPreferenceBase(BaseModel):
    preferred_pet_type: Optional[str] = None
    preferred_age_range: Optional[str] = None
    preferred_size: Optional[str] = None
    accept_special_care: bool = False
    accept_high_energy: bool = False


class UserPreferenceCreate(UserPreferenceBase):
    pass


class UserPreferenceUpdate(UserPreferenceBase):
    pass


class UserPreferenceOut(UserPreferenceBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
2. app/schemas/pet_feature_schema.py
from pydantic import BaseModel
from typing import Optional


class PetFeatureBase(BaseModel):
    energy_level: Optional[str] = None
    care_level: Optional[str] = None
    beginner_friendly: bool = True
    social_level: Optional[str] = None
    special_care_flag: bool = False


class PetFeatureCreate(PetFeatureBase):
    pass


class PetFeatureUpdate(PetFeatureBase):
    pass


class PetFeatureOut(PetFeatureBase):
    id: int
    pet_id: int

    class Config:
        from_attributes = True


class PetRequirementBase(BaseModel):
    require_experience: bool = False
    require_stable_housing: bool = False
    require_return_visit: bool = False
    region_limit: Optional[str] = None


class PetRequirementCreate(PetRequirementBase):
    pass


class PetRequirementUpdate(PetRequirementBase):
    pass


class PetRequirementOut(PetRequirementBase):
    id: int
    pet_id: int

    class Config:
        from_attributes = True
五、Service 层
1. app/service/profile_service.py
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.models.user_preference import UserPreference
from app.schemas.profile_schema import (
    UserProfileCreate,
    UserProfileUpdate,
    UserPreferenceCreate,
    UserPreferenceUpdate,
)


class ProfileService:
    @staticmethod
    def get_profile(db: Session, user_id: int):
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    @staticmethod
    def upsert_profile(db: Session, user_id: int, data: UserProfileCreate | UserProfileUpdate):
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

        if not profile:
            profile = UserProfile(user_id=user_id, **data.model_dump())
            db.add(profile)
        else:
            for key, value in data.model_dump().items():
                setattr(profile, key, value)

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_preference(db: Session, user_id: int):
        return db.query(UserPreference).filter(UserPreference.user_id == user_id).first()

    @staticmethod
    def upsert_preference(db: Session, user_id: int, data: UserPreferenceCreate | UserPreferenceUpdate):
        preference = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()

        if not preference:
            preference = UserPreference(user_id=user_id, **data.model_dump())
            db.add(preference)
        else:
            for key, value in data.model_dump().items():
                setattr(preference, key, value)

        db.commit()
        db.refresh(preference)
        return preference
2. app/service/pet_feature_service.py
from sqlalchemy.orm import Session

from app.models.pet_feature import PetFeature
from app.models.pet_requirement import PetRequirement
from app.schemas.pet_feature_schema import (
    PetFeatureCreate,
    PetFeatureUpdate,
    PetRequirementCreate,
    PetRequirementUpdate,
)


class PetFeatureService:
    @staticmethod
    def get_feature(db: Session, pet_id: int):
        return db.query(PetFeature).filter(PetFeature.pet_id == pet_id).first()

    @staticmethod
    def upsert_feature(db: Session, pet_id: int, data: PetFeatureCreate | PetFeatureUpdate):
        feature = db.query(PetFeature).filter(PetFeature.pet_id == pet_id).first()

        if not feature:
            feature = PetFeature(pet_id=pet_id, **data.model_dump())
            db.add(feature)
        else:
            for key, value in data.model_dump().items():
                setattr(feature, key, value)

        db.commit()
        db.refresh(feature)
        return feature

    @staticmethod
    def get_requirement(db: Session, pet_id: int):
        return db.query(PetRequirement).filter(PetRequirement.pet_id == pet_id).first()

    @staticmethod
    def upsert_requirement(db: Session, pet_id: int, data: PetRequirementCreate | PetRequirementUpdate):
        requirement = db.query(PetRequirement).filter(PetRequirement.pet_id == pet_id).first()

        if not requirement:
            requirement = PetRequirement(pet_id=pet_id, **data.model_dump())
            db.add(requirement)
        else:
            for key, value in data.model_dump().items():
                setattr(requirement, key, value)

        db.commit()
        db.refresh(requirement)
        return requirement
六、Router 层
1. app/router/profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.profile_schema import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileOut,
    UserPreferenceCreate,
    UserPreferenceUpdate,
    UserPreferenceOut,
)
from app.service.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{user_id}", response_model=UserProfileOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = ProfileService.get_profile(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户画像不存在")
    return profile


@router.put("/{user_id}", response_model=UserProfileOut)
def upsert_profile(user_id: int, payload: UserProfileUpdate, db: Session = Depends(get_db)):
    return ProfileService.upsert_profile(db, user_id, payload)


@router.get("/{user_id}/preference", response_model=UserPreferenceOut)
def get_preference(user_id: int, db: Session = Depends(get_db)):
    preference = ProfileService.get_preference(db, user_id)
    if not preference:
        raise HTTPException(status_code=404, detail="用户偏好不存在")
    return preference


@router.put("/{user_id}/preference", response_model=UserPreferenceOut)
def upsert_preference(user_id: int, payload: UserPreferenceUpdate, db: Session = Depends(get_db)):
    return ProfileService.upsert_preference(db, user_id, payload)
2. app/router/pet_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pet_feature_schema import (
    PetFeatureUpdate,
    PetFeatureOut,
    PetRequirementUpdate,
    PetRequirementOut,
)
from app.service.pet_feature_service import PetFeatureService

router = APIRouter(prefix="/pets", tags=["pet-feature"])


@router.get("/{pet_id}/feature", response_model=PetFeatureOut)
def get_pet_feature(pet_id: int, db: Session = Depends(get_db)):
    feature = PetFeatureService.get_feature(db, pet_id)
    if not feature:
        raise HTTPException(status_code=404, detail="宠物特征不存在")
    return feature


@router.put("/{pet_id}/feature", response_model=PetFeatureOut)
def upsert_pet_feature(pet_id: int, payload: PetFeatureUpdate, db: Session = Depends(get_db)):
    return PetFeatureService.upsert_feature(db, pet_id, payload)


@router.get("/{pet_id}/requirement", response_model=PetRequirementOut)
def get_pet_requirement(pet_id: int, db: Session = Depends(get_db)):
    requirement = PetFeatureService.get_requirement(db, pet_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="宠物领养要求不存在")
    return requirement


@router.put("/{pet_id}/requirement", response_model=PetRequirementOut)
def upsert_pet_requirement(pet_id: int, payload: PetRequirementUpdate, db: Session = Depends(get_db)):
    return PetFeatureService.upsert_requirement(db, pet_id, payload)
七、主程序注册路由

在 main.py 或统一路由注册文件里补：

from app.router import profile, pet_feature

app.include_router(profile.router)
app.include_router(pet_feature.router)
八、如果你暂时不用 Alembic，先手工建表也行

如果你现在项目赶时间，先用 SQLite 手工执行 SQL 也可以：

CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    housing_type VARCHAR(50),
    housing_size VARCHAR(50),
    rental_status VARCHAR(50),
    pet_experience BOOLEAN DEFAULT 0,
    available_time VARCHAR(50),
    family_support BOOLEAN DEFAULT 0,
    budget_level VARCHAR(50),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    preferred_pet_type VARCHAR(50),
    preferred_age_range VARCHAR(50),
    preferred_size VARCHAR(50),
    accept_special_care BOOLEAN DEFAULT 0,
    accept_high_energy BOOLEAN DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

CREATE TABLE pet_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL UNIQUE,
    energy_level VARCHAR(50),
    care_level VARCHAR(50),
    beginner_friendly BOOLEAN DEFAULT 1,
    social_level VARCHAR(50),
    special_care_flag BOOLEAN DEFAULT 0,
    FOREIGN KEY(pet_id) REFERENCES pets(id) ON DELETE CASCADE
);

CREATE TABLE pet_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL UNIQUE,
    require_experience BOOLEAN DEFAULT 0,
    require_stable_housing BOOLEAN DEFAULT 0,
    require_return_visit BOOLEAN DEFAULT 0,
    region_limit VARCHAR(100),
    FOREIGN KEY(pet_id) REFERENCES pets(id) ON DELETE CASCADE
);
九、这一步做完后，你就具备了什么

做完这一步，你已经拿到了推荐流水线最前面的输入层：

用户侧可用特征
居住条件
养宠经验
时间投入
家庭支持
预算
偏好类型
宠物侧可用特征
活动量
照护难度
是否适合新手
社交程度
是否需要特殊照护
约束侧可用特征
是否要求经验
是否要求稳定住房
是否接受回访
地区限制

这时你下一步就可以正式写：

recommendation 模块 + pipeline 骨架

这一步代码接完以后，下一步就不是继续补表了，而是：

新增 recommendation 模块骨架

先做这几个文件：

app/recommendation/query.py
app/recommendation/candidate.py
app/recommendation/pipeline.py
app/recommendation/sources/available_pet_source.py
app/recommendation/hydrators/pet_feature_hydrator.py
app/recommendation/filters/hard_constraint_filter.py
app/recommendation/scorers/multi_feature_scorer.py
app/recommendation/selectors/topk_selector.py

这是你真正开始借鉴 X 核心流程的地方。

十一、你现在最该先验证的接口

这几个接口跑通就够了：

PUT /profile/{user_id}
PUT /profile/{user_id}/preference
PUT /pets/{pet_id}/feature
PUT /pets/{pet_id}/requirement

只要这四个能存进去、能查出来，这一步就成功。

十二、我建议你马上开始的顺序

先建表。
再写 models。
再写 schemas。
再写 service。
最后补 router。

这样最稳。