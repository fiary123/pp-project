1. 后端新增一个 profile 模块

不要再把这些字段塞在 user 里混着写。

建议新增：

app/router/profile.py
app/service/profile_service.py
app/models/user_profile.py
app/models/user_preference.py
app/schemas/profile_schema.py
2. 数据库先加 4 张核心表

这是第一步里最重要的部分。

user_profiles

存基础领养条件

字段建议：

id
user_id
housing_type 住房类型
housing_size 居住空间
rental_status 是否租房
pet_experience 是否有养宠经验
available_time 每日可投入时间
family_support 家庭是否支持
budget_level 预算承受能力
user_preferences

存领养偏好

字段建议：

id
user_id
preferred_pet_type
preferred_age_range
preferred_size
accept_special_care
accept_high_energy
pet_features

存推荐特征，不是基础宠物信息

字段建议：

id
pet_id
energy_level
care_level
beginner_friendly
social_level
special_care_flag
pet_requirements

存发布者领养要求

字段建议：

id
pet_id
require_experience
require_stable_housing
require_return_visit
region_limit
这一步改完，你就完成了什么

你就完成了 X 流水线里的两段雏形：

hydrate_query

把用户画像和偏好加载进推荐请求

hydrate

把宠物特征和送养要求补到候选对象上

这时候你还没写打分器，但已经把最难的基础打好了。
你当前第一步不要做什么

现在先不要：

先训练模型
先改 ai 模块
先做复杂推荐页面
先写一大堆评分公式
先做申请人排序

这些都应该放后面。

因为现在你最缺的是：
推荐输入字段的标准化和结构化。

按你当前项目，第一步的最小落地目标

你现在这一轮修改，只要先做到下面 3 件事就够了：

目标 1

用户可以填写并保存“领养画像”

目标 2

每只宠物除了基础信息外，还能补充“推荐特征”和“领养要求”

目标 3

后端能提供一个统一接口，把这些数据查出来

第一批接口就做这几个
用户侧
GET /profile/{user_id}
PUT /profile/{user_id}
GET /profile/{user_id}/preferences
PUT /profile/{user_id}/preferences
宠物侧
GET /pets/{pet_id}/features
PUT /pets/{pet_id}/features
GET /pets/{pet_id}/requirements
PUT /pets/{pet_id}/requirements

只做这些，不要贪多。

为什么这一步最适合你现在动手

因为它同时满足三件事：

1. 和你当前项目兼容

你现在就是 FastAPI 的 router-service 分层，这一步很好插进去。

2. 和 X 的核心流程一致

虽然你不训练模型，但你已经开始按它的“阶段化推荐流水线”重构了。

3. 对论文也最有价值

这一改，你论文里马上就能写：

用户画像构建
宠物特征建模
领养约束建模

这三块都是很实的内容。

我建议你把“第一步”定义成一句话

你可以直接记成：

先完成推荐输入层改造，新增用户画像、领养偏好、宠物特征和领养要求四类结构化数据。

这就是你现在该做的第一步。

如果你要更具体到文件级别

你现在就先新建这些文件：

app/router/profile.py
app/service/profile_service.py
app/models/user_profile.py
app/models/user_preference.py
app/models/pet_feature.py
app/models/pet_requirement.py
app/schemas/profile_schema.py
app/schemas/pet_feature_schema.py

然后先把数据库表建出来，再补接口。

最后给你一个非常明确的执行顺序

今天就先做这 4 件事：

新增 user_profiles 表
新增 user_preferences 表
新增 pet_features 和 pet_requirements 表
新增 profile.py 路由，完成用户画像和偏好的增删改查

这四个做完，才进入下一步：
写 recommendation 模块和 pipeline 骨架。