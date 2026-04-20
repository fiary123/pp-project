"""
种子数据脚本 - 一键填充演示数�?
运行方式: python scripts/seed_data.py
包含: 用户、宠�?30�?、社区帖�?25�?、评论、公告、领养申�?
"""
import sys
import os
import json
import sqlite3
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database.db_config import SQLITE_DB_PATH
from src.web.services.db_service import get_db_connection, ensure_tables
# 种子数据使用明文密码（兼�?auth_service 中的明文回退逻辑�?
def _seed_password(plain: str) -> str:
    return plain

# ── Unsplash 图片（稳定可访问的直链，按分类整理）──────────────────────────
CAT_IMAGES = [
    "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&auto=format",
    "https://images.unsplash.com/photo-1533738363-b7f9aef128ce?w=600&auto=format",
    "https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=600&auto=format",
    "https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=600&auto=format",
    "https://images.unsplash.com/photo-1506755855567-92ff770e8d00?w=600&auto=format",
    "https://images.unsplash.com/photo-1548247416-ec66f4900b2e?w=600&auto=format",
    "https://images.unsplash.com/photo-1561948955-570b270e7c36?w=600&auto=format",
    "https://images.unsplash.com/photo-1592194996308-7b43878e84a6?w=600&auto=format",
    "https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?w=600&auto=format",
    "https://images.unsplash.com/photo-1518791841217-8f162f1912da?w=600&auto=format",
]
DOG_IMAGES = [
    "https://images.unsplash.com/photo-1552053831-71594a27632d?w=600&auto=format",
    "https://images.unsplash.com/photo-1503256207526-0df5d6342a00?w=600&auto=format",
    "https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?w=600&auto=format",
    "https://images.unsplash.com/photo-1529429617329-8a79e088c02c?w=600&auto=format",
    "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=600&auto=format",
    "https://images.unsplash.com/photo-1477884213360-7e9d7dcc1e48?w=600&auto=format",
    "https://images.unsplash.com/photo-1537123547273-e59f4f9f639b?w=600&auto=format",
    "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=600&auto=format",
    "https://images.unsplash.com/photo-1534361960057-19f4434a5d61?w=600&auto=format",
    "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=600&auto=format",
]
POST_IMAGES = [
    "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800&auto=format",
    "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&auto=format",
    "https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=800&auto=format",
    "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=800&auto=format",
    "https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800&auto=format",
    "https://images.unsplash.com/photo-1548247416-ec66f4900b2e?w=800&auto=format",
    "https://images.unsplash.com/photo-1561948955-570b270e7c36?w=800&auto=format",
    "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=800&auto=format",
    "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=800&auto=format",
    "https://images.unsplash.com/photo-1518791841217-8f162f1912da?w=800&auto=format",
    "https://images.unsplash.com/photo-1477884213360-7e9d7dcc1e48?w=800&auto=format",
    "https://images.unsplash.com/photo-1506755855567-92ff770e8d00?w=800&auto=format",
    None, None, None,  # 部分帖子无图，更真实
]

# ── 用户数据 ────────────────────────────────────────────────────────────────
USERS = [
    {"username": "用户A", "email": "user@test.com",  "password": "123456", "role": "user"},
    {"username": "爱宠救助�?, "email": "admin@test.com", "password": "admin123", "role": "admin"},
    {"username": "系统管理�?, "email": "root@test.com",  "password": "root123",  "role": "root"},
    {"username": "喵星人控",   "email": "miao@test.com",  "password": "123456",   "role": "user"},
    {"username": "汪星�?,     "email": "wang@test.com",  "password": "123456",   "role": "user"},
    {"username": "宠物医院",   "email": "vet@test.com",   "password": "vet123",   "role": "admin"},
    {"username": "萌宠爱好�?, "email": "fan@test.com",   "password": "123456",   "role": "user"},
    {"username": "橘猫饲主",   "email": "jucat@test.com", "password": "123456",   "role": "user"},
]

# ── 宠物数据�?0条）────────────────────────────────────────────────────────
PETS = [
    # 猫咪 (15�?
    {
        "name": "饼干", "species": "英国短毛�?, "age": 2,
        "is_shedding": "适量", "energy_level": "温和",
        "description": "性格温顺沉稳，喜欢在阳光下打盹。有一双圆圆的铜色眼睛，非常漂亮。适合安静的家庭�?,
        "tags": ["温顺", "安静", "适合新手"], "image": CAT_IMAGES[0], "owner_id": 2,
    },
    {
        "name": "小虎", "species": "橘猫", "age": 1,
        "is_shedding": "较多", "energy_level": "活跃",
        "description": "标准橘猫，能吃能睡，非常粘人。每天必须要抱抱才肯罢休，是个小暖炉�?,
        "tags": ["粘人", "活泼", "橘猫"], "image": CAT_IMAGES[1], "owner_id": 2,
    },
    {
        "name": "雪球", "species": "波斯�?, "age": 3,
        "is_shedding": "较多", "energy_level": "�?,
        "description": "一身雪白长毛，优雅高贵。性格独立，不爱吵闹，适合有耐心定期梳毛的主人�?,
        "tags": ["优雅", "独立", "长毛"], "image": CAT_IMAGES[2], "owner_id": 2,
    },
    {
        "name": "墨墨", "species": "孟买�?, "age": 2,
        "is_shedding": "�?, "energy_level": "中等",
        "description": "全身黑色亮丽，像一只迷你黑豹。好奇心强，喜欢探索家里的每个角落�?,
        "tags": ["全黑", "好奇", "聪明"], "image": CAT_IMAGES[3], "owner_id": 2,
    },
    {
        "name": "布丁", "species": "布偶�?, "age": 1,
        "is_shedding": "适量", "energy_level": "温和",
        "description": "蓝眼布偶，被抱起来就软绵绵趴着，完全不挣扎，名副其实的'布偶'�?,
        "tags": ["温柔", "抱抱", "蓝眼�?], "image": CAT_IMAGES[4], "owner_id": 2,
    },
    {
        "name": "花花", "species": "三花�?, "age": 4,
        "is_shedding": "适量", "energy_level": "中等",
        "description": "三花猫，花纹非常漂亮。成熟稳重，已做绝育，健康状况良好，疫苗已完成�?,
        "tags": ["三花", "已绝�?, "成年"], "image": CAT_IMAGES[5], "owner_id": 6,
    },
    {
        "name": "咖啡", "species": "阿比西尼亚猫", "age": 2,
        "is_shedding": "�?, "energy_level": "�?,
        "description": "运动型猫咪，跑跳能力一流。聪明活泼，需要主人多陪它互动，不适合长期独处�?,
        "tags": ["运动", "聪明", "需互动"], "image": CAT_IMAGES[6], "owner_id": 2,
    },
    {
        "name": "奶茶", "species": "暹罗�?, "age": 3,
        "is_shedding": "适量", "energy_level": "活跃",
        "description": "标准暹罗，爱说话，会用各种声音和你交流。极其粘人，不能接受主人不理它�?,
        "tags": ["话痨", "粘人", "暹罗"], "image": CAT_IMAGES[7], "owner_id": 2,
    },
    {
        "name": "豆豆", "species": "苏格兰折耳猫", "age": 2,
        "is_shedding": "适量", "energy_level": "温和",
        "description": "折耳造型超可爱，经常呆坐一脸困惑的表情。性格温和，喜欢被摸头�?,
        "tags": ["折�?, "呆萌", "温和"], "image": CAT_IMAGES[8], "owner_id": 2,
    },
    {
        "name": "虎纹", "species": "美国短毛�?, "age": 5,
        "is_shedding": "适量", "energy_level": "中等",
        "description": "经典银色虎纹，身体健壮。已绝育，打过全套疫苗。性格随和，和小孩相处融洽�?,
        "tags": ["虎纹", "已绝�?, "亲小�?], "image": CAT_IMAGES[9], "owner_id": 6,
    },
    {
        "name": "糖糖", "species": "缅因�?, "age": 2,
        "is_shedding": "较多", "energy_level": "活跃",
        "description": "大型猫种，毛发厚实蓬松，像个小狮子。性格温柔像狗狗一样忠诚，会跟着主人走�?,
        "tags": ["大型", "温柔", "像狗的猫"], "image": CAT_IMAGES[0], "owner_id": 2,
    },
    {
        "name": "蓝莓", "species": "俄罗斯蓝�?, "age": 1,
        "is_shedding": "�?, "energy_level": "中等",
        "description": "蓝灰色短毛，绿色眼睛，气质高冷。对陌生人有些警惕，但和熟悉的人非常亲近�?,
        "tags": ["高冷", "绿眼", "低敏�?], "image": CAT_IMAGES[1], "owner_id": 2,
    },
    {
        "name": "胖橘", "species": "橘猫", "age": 3,
        "is_shedding": "较多", "energy_level": "�?,
        "description": "资深吃货，体型圆润，每天最大的爱好就是吃饭和睡觉。非常治愈，每次摸它都很解压�?,
        "tags": ["圆润", "吃货", "解压"], "image": CAT_IMAGES[2], "owner_id": 2,
    },
    {
        "name": "芝士", "species": "金吉拉猫", "age": 2,
        "is_shedding": "较多", "energy_level": "温和",
        "description": "毛色如金色丝绸，眼睛翠绿。性情温顺，适合喜欢安静的家庭，需要定期专业梳理毛发�?,
        "tags": ["金色", "温顺", "长毛"], "image": CAT_IMAGES[3], "owner_id": 6,
    },
    {
        "name": "可乐", "species": "无毛�?, "age": 2,
        "is_shedding": "�?, "energy_level": "活跃",
        "description": "斯芬克斯无毛猫，皮肤温热柔软，像个小暖炉。对过敏人群友好，性格热情爱撒娇�?,
        "tags": ["无毛", "低过�?, "热情"], "image": CAT_IMAGES[4], "owner_id": 2,
    },
    # 狗狗 (15�?
    {
        "name": "球球", "species": "金毛寻回�?, "age": 2,
        "is_shedding": "较多", "energy_level": "�?,
        "description": "阳光开朗的金毛，笑起来超治愈。训练度高，会握手、坐下、趴下。非常适合有院子的家庭�?,
        "tags": ["金毛", "温顺", "适合家庭"], "image": DOG_IMAGES[0], "owner_id": 2,
    },
    {
        "name": "小黑", "species": "拉布拉多�?, "age": 1,
        "is_shedding": "中等", "energy_level": "�?,
        "description": "黑色拉布拉多，聪明易训，已完成基础服从训练。活力十足，每天需要充分的户外运动�?,
        "tags": ["聪明", "易训�?, "运动�?], "image": DOG_IMAGES[1], "owner_id": 2,
    },
    {
        "name": "棉花�?, "species": "萨摩耶犬", "age": 2,
        "is_shedding": "非常�?, "energy_level": "�?,
        "description": "微笑天使萨摩耶，雪白毛发笑容永远在线。非常粘人，每天要大量运动，换毛期需要勤打扫�?,
        "tags": ["萨摩�?, "微笑", "粘人"], "image": DOG_IMAGES[2], "owner_id": 2,
    },
    {
        "name": "豆沙", "species": "柯基�?, "age": 3,
        "is_shedding": "较多", "energy_level": "中等",
        "description": "屁股最迷人的柯基！腿短但步伐矫健，喜欢奔跑。会'弹跳�?，看着超级搞笑可爱�?,
        "tags": ["柯基", "短腿", "可爱"], "image": DOG_IMAGES[3], "owner_id": 2,
    },
    {
        "name": "毛毛", "species": "博美�?, "age": 2,
        "is_shedding": "较多", "energy_level": "活跃",
        "description": "毛茸茸的小球，但性格一点不软！脾气倔强，认定了主人就非常忠诚。小型犬适合公寓饲养�?,
        "tags": ["博美", "小型", "忠诚"], "image": DOG_IMAGES[4], "owner_id": 2,
    },
    {
        "name": "大壮", "species": "德国牧羊�?, "age": 4,
        "is_shedding": "较多", "energy_level": "�?,
        "description": "警犬血统，已完成高级训练。忠诚护主，对陌生人保持警惕。需要有经验的主人和充足的活动空间�?,
        "tags": ["护主", "高级训练", "有经验主�?], "image": DOG_IMAGES[5], "owner_id": 6,
    },
    {
        "name": "花生", "species": "比格�?, "age": 2,
        "is_shedding": "适量", "energy_level": "�?,
        "description": "嗅觉猎犬，好奇心爆棚，每次出门都要把每棵树都闻遍。活泼开朗，爱和小孩子玩�?,
        "tags": ["比格", "好奇", "亲小�?], "image": DOG_IMAGES[6], "owner_id": 2,
    },
    {
        "name": "奥利�?, "species": "边境牧羊�?, "age": 3,
        "is_shedding": "中等", "energy_level": "极高",
        "description": "智商顶尖的边牧，需要大量脑力和体力活动。会飞盘、敏捷障碍。非常适合喜欢运动的主人�?,
        "tags": ["边牧", "聪明", "运动达人"], "image": DOG_IMAGES[7], "owner_id": 2,
    },
    {
        "name": "冰淇�?, "species": "哈士�?, "age": 2,
        "is_shedding": "非常�?, "energy_level": "极高",
        "description": "二哈本哈，拆家届的老前辈。但颜值超高，蓝眼睛特别迷人。需要主人有强大的心理素质�?,
        "tags": ["哈士�?, "高颜�?, "精力充沛"], "image": DOG_IMAGES[8], "owner_id": 2,
    },
    {
        "name": "豆腐", "species": "泰迪�?, "age": 1,
        "is_shedding": "�?, "energy_level": "中等",
        "description": "棕色泰迪，不掉毛，对过敏人群友好。经过专业修剪造型可爱，适合公寓饲养�?,
        "tags": ["泰迪", "不掉�?, "低过�?], "image": DOG_IMAGES[9], "owner_id": 2,
    },
    {
        "name": "小白", "species": "西高地白�?, "age": 3,
        "is_shedding": "�?, "energy_level": "中等",
        "description": "全白小型梗犬，精神抖擞。已完成基础训练，性格勇敢有主见。适合有养宠经验的家庭�?,
        "tags": ["梗犬", "勇敢", "小型"], "image": DOG_IMAGES[0], "owner_id": 6,
    },
    {
        "name": "芒果", "species": "柴犬", "age": 2,
        "is_shedding": "较多", "energy_level": "中等",
        "description": "网红柴犬，微笑自带滤镜。性格独立，有自己的想法，但对主人非常忠诚，是安静的陪伴者�?,
        "tags": ["柴犬", "网红", "独立"], "image": DOG_IMAGES[1], "owner_id": 2,
    },
    {
        "name": "葡萄", "species": "迷你雪纳�?, "age": 4,
        "is_shedding": "�?, "energy_level": "中等",
        "description": "迷你雪纳瑞，胡须标志性。不掉毛，活泼但不过分吵闹，非常适合公寓家庭，警觉性高�?,
        "tags": ["雪纳�?, "不掉�?, "公寓友好"], "image": DOG_IMAGES[2], "owner_id": 2,
    },
    {
        "name": "咕噜", "species": "法国斗牛�?, "age": 3,
        "is_shedding": "�?, "energy_level": "�?,
        "description": "法斗，懒洋洋的小胖子。打呼噜的声音超级治愈，活动量不大，非常适合都市公寓生活�?,
        "tags": ["法斗", "慵懒", "公寓友好"], "image": DOG_IMAGES[3], "owner_id": 2,
    },
    {
        "name": "珍珠", "species": "贵宾�?, "age": 2,
        "is_shedding": "�?, "energy_level": "中等",
        "description": "标准贵宾，卷毛不掉毛。聪明易训，会很多才艺。性格友好，与小孩和老人都能相处融洽�?,
        "tags": ["贵宾", "聪明", "不掉�?, "亲人"], "image": DOG_IMAGES[4], "owner_id": 6,
    },
]

# ── 社区帖子�?5条）──────────────────────────────────────────────────────
POSTS = [
    # 日常晒宠 (daily)
    {
        "title": "今天的饼干又胖了一点点",
        "content": "称了下体重，英短又长�?.2kg……兽医说要控食了，但它那可怜巴巴的眼神我真的受不了 😭 有没有好用的猫咪自动喂食器推荐？",
        "type": "daily", "user_idx": 3, "likes": 42, "image_idx": 0,
        "days_ago": 1,
    },
    {
        "title": "金毛第一次下海，反应把我笑死�?,
        "content": "带球球去海边玩，以为它会很喜欢水，结果第一个浪打来直接跑路……后来慢慢才敢靠近，最后还是玩得很开心！分享几张照片给大�?,
        "type": "daily", "user_idx": 4, "likes": 87, "image_idx": 1,
        "days_ago": 2,
    },
    {
        "title": "橘猫语录：食物是第一生产�?,
        "content": "每次我进厨房，不管睡多死，小虎一定第一个到场。它就坐在那里用眼神审判我，意思是'你要是不给我吃的就等着'。今天终于拍到了这神情，哈哈�?,
        "type": "daily", "user_idx": 7, "likes": 156, "image_idx": 2,
        "days_ago": 1,
    },
    {
        "title": "柯基的屁股永远是最好看�?,
        "content": "今天出门遛弯，前面走来一只柯基，整条街的人都在看它的屁股……太可爱了忍不住拍了下来，狗主人也很大方地让我摸了一下，软乎乎的�?,
        "type": "daily", "user_idx": 5, "likes": 203, "image_idx": 3,
        "days_ago": 3,
    },
    {
        "title": "猫咪把我新买的耳机咬断了…�?,
        "content": "600块的耳机，就这么没了。它咬断之后还若无其事地在旁边舔爪子。我气到想还它，但看见那张脸又气不起来……宠物真的是人类的天�?,
        "type": "daily", "user_idx": 3, "likes": 318, "image_idx": 4,
        "days_ago": 5,
    },
    {
        "title": "萨摩耶换毛季求生指南",
        "content": "棉花糖又开始换毛了，今天打扫出来的毛能织一件毛衣……整理了几个心得：①每天梳毛20分钟 ②多补充ω3 ③买一个好吸力的宠物吸尘器，真的救�?,
        "type": "daily", "user_idx": 4, "likes": 95, "image_idx": 5,
        "days_ago": 4,
    },
    {
        "title": "三岁布偶猫，还是那么黏人",
        "content": "布丁今天又来占领我的键盘，我打字它就把脑袋怼过来，一�?你不理我我就给你添乱'的态度。爱了爱了，工作效率为零但心情好极了",
        "type": "daily", "user_idx": 6, "likes": 72, "image_idx": 6,
        "days_ago": 2,
        "days_ago": 2,
    },
    {
        "title": "边牧飞盘训练记录�?0�?,
        "content": "奥利奥的飞盘技术越来越好了！今天练习了单手接盘，成功率达到�?0%。分享一下训练日志：第一周先练习衔取，第二周引入飞盘目标，第三周开始抛接…�?,
        "type": "daily", "user_idx": 4, "likes": 134, "image_idx": 7,
        "days_ago": 6,
    },
    # 求助�?(help)
    {
        "title": "【求助】猫咪突然不爱吃东西，要紧吗�?,
        "content": "我家英短今天早上没吃早饭，中午喂猫粮也只吃了几口就走了。精神看起来还好，但平时都是秒光的。需要去看医生吗还是等等看？已经养了3年了，从没遇到过这种情况",
        "type": "help", "user_idx": 3, "likes": 23, "image_idx": None,
        "days_ago": 1,
    },
    {
        "title": "【求助】狗狗打疫苗后一直在发抖，正常吗",
        "content": "今天带球球去打了五联苗，回来之后就一直微微发抖，食欲也差了很多。医生说可能是正常应激反应，但我还是很担心。有没有遇到过同样情况的朋友�?,
        "type": "help", "user_idx": 4, "likes": 15, "image_idx": None,
        "days_ago": 1,
    },
    {
        "title": "【紧急求助】猫咪误食了葡萄，怎么�?,
        "content": "刚才一不注意，花花把桌上的几颗葡萄给吃了，大概3-4颗。我知道葡萄对猫咪有毒，现在非常紧张，要马上去医院吗？她现在看起来还好，没有呕吐",
        "type": "help", "user_idx": 6, "likes": 8, "image_idx": None,
        "days_ago": 0,
    },
    {
        "title": "【求助】两只猫打架怎么和解",
        "content": "家里原来有一只三岁的猫，上个月又领养了一只小猫，结果老猫一直攻击新猫……已经分开养了两周了，不知道怎么才能让它们和平共处，求经验帖�?,
        "type": "help", "user_idx": 7, "likes": 31, "image_idx": None,
        "days_ago": 3,
    },
    {
        "title": "【求推荐】北京东城区靠谱宠物医院",
        "content": "最近搬到东城区，原来常去的医院太远了。求推荐东城区附近靠谱的宠物医院，最好有猫科专门诊室的，不介意贵一点但要技术好",
        "type": "help", "user_idx": 3, "likes": 19, "image_idx": None,
        "days_ago": 5,
    },
    # 知识分享 (knowledge)
    {
        "title": "猫咪绝育后的护理要点整理",
        "content": "刚给家里的奶茶做完绝育手术，整理了一份术后护理清单给大家参考：\n1. 术后24小时禁食禁水（除非医嘱）\n2. 使用脖圈防止舔舐伤口\n3. 避免剧烈运动至少7天\n4. 每天检查伤口是否红肿渗液\n5. 按时复诊拆线\n希望对大家有帮助�?,
        "type": "knowledge", "user_idx": 6, "likes": 247, "image_idx": 8,
        "days_ago": 7,
    },
    {
        "title": "新手养狗必看：第一年疫苗时间表",
        "content": "很多新手不清楚幼犬疫苗怎么打，整理了一下标准流程：\n- 6-8周龄：第一针五联苗\n- 10-12周龄：第二针五联苗\n- 14-16周龄：第三针五联�?狂犬疫苗\n- 此后每年加强一次\n注意：打完疫苗三天内不要洗澡�?,
        "type": "knowledge", "user_idx": 5, "likes": 189, "image_idx": 9,
        "days_ago": 10,
    },
    {
        "title": "猫咪不同叫声代表什么？读懂它的语言",
        "content": "养猫三年总结的猫语词典：\n🔊 短促高音'�?= 打招呼\n🔊 拉长�?喵~'= 我要吃饭\n🔊 低沉咕噜�? 我很满足\n🔊 颤抖的颤�? 我在生气/警告\n🔊 嚎叫= 我不舒服或发情\n最近发现用AI分析宠物语音也挺准的，大家可以试�?,
        "type": "knowledge", "user_idx": 3, "likes": 312, "image_idx": 10,
        "days_ago": 8,
    },
    {
        "title": "夏季宠物防暑降温完整指南",
        "content": "夏天来了，宠物中暑是很危险的！分享几个实用技巧：\n①保证室内通风，气温超�?0度要开空调\n②出门选择早晨8点前或晚�?点后\n③随时备好饮用水\n④地面温度超�?0度会烫伤爪垫，摸一下地面判断\n⑤出现喘气急促、口水多、无力要立即就医",
        "type": "knowledge", "user_idx": 6, "likes": 156, "image_idx": 11,
        "days_ago": 15,
    },
    {
        "title": "狗狗分离焦虑怎么训练？三个月成功案例",
        "content": "我家二哈冰淇淋之前严重分离焦虑，一个人在家就会一直叫、破坏东西。经过三个月的系统训练，现在已经可以独处4小时了。方法：循序渐进离开→积极强化安静行为→增加益智玩具……详细分享在评论�?,
        "type": "knowledge", "user_idx": 4, "likes": 98, "image_idx": 0,
        "days_ago": 12,
    },
    # 领养分享 (adoption)
    {
        "title": "成功领养半年后的感想",
        "content": "半年前通过这个平台领养了花花，现在她已经完全融入我们家了。当初还担心成年猫会不亲人，没想到她超级粘我。感谢平台的智能匹配功能，真的帮我找到了最合适的小伙伴！",
        "type": "adoption", "user_idx": 3, "likes": 67, "image_idx": 5,
        "days_ago": 0,
    },
    {
        "title": "领养前你需要了解的10件事",
        "content": "作为已经领养�?只猫�?老鸟'，总结了几点新手必看：\n1. 领养不冲动，充分了解该宠物的性格\n2. 提前准备好基础物资\n3. 给新�?狗至�?周的适应期\n4. 不要因为不融合就退回\n5. 做好长达15年的陪伴准备…�?,
        "type": "adoption", "user_idx": 7, "likes": 203, "image_idx": 6,
        "days_ago": 20,
    },
    {
        "title": "我们终于给边牧找到了好家庭！",
        "content": "经过两个月的审核，奥利奥的新主人终于确定了！是一对年轻夫妻，有自己的院子，男主人还是马拉松爱好者。相信奥利奥会非常幸福的。作为救助站志愿者，每次送养成功都很感动",
        "type": "adoption", "user_idx": 6, "likes": 445, "image_idx": 7,
        "days_ago": 3,
    },
    # 公益活动 (charity)
    {
        "title": "【公益】本周末社区流浪猫绝育活�?,
        "content": "本周六上�?点到12点，在朝阳区望京社区活动中心开展流浪猫TNR（诱�?绝育-放归）活动。需要志愿者参与协助，提供专业兽医上门支持。有意愿的朋友请私信报名�?,
        "type": "charity", "user_idx": 6, "likes": 88, "image_idx": 8,
        "days_ago": 2,
    },
    {
        "title": "【募集】为流浪犬收容站筹集过冬物资",
        "content": "北京入冬了，我们救助站的流浪犬急需：旧毛毯/棉被、狗粮（成犬粮优先）、保温垫。不接受现金，只接受实物捐赠。地址：朝阳区xxx街xxx号，联系人：李老师，电话：1xxx�?,
        "type": "charity", "user_idx": 6, "likes": 156, "image_idx": 9,
        "days_ago": 7,
    },
    {
        "title": "感谢所有参与领养节活动的朋�?,
        "content": "上周末的'缘分领养�?圆满结束！共�?8只猫咪和12只狗狗找到了新家。特别感谢现场志愿者团队、赞助商、以及每一位来咨询的朋友。即使没有领养，来了解和学习也很重要❤️",
        "type": "charity", "user_idx": 6, "likes": 521, "image_idx": 10,
        "days_ago": 9,
    },
    {
        "title": "用AI智能分诊拯救了我的猫——真实经历分�?,
        "content": "上周凌晨2点，猫咪突然开始一直用力蹲厕所但没有尿出来。我用了平台的AI分诊功能，系统直接判定为'紧急就�?并说明可能是尿路堵塞。我立刻去了24小时宠物医院，确诊了！医生说再晚几小时可能会引发肾衰竭。真的太感谢这个功能�?,
        "type": "daily", "user_idx": 3, "likes": 734, "image_idx": 11,
        "days_ago": 14,
    },
]

# ── 评论数据 ────────────────────────────────────────────────────────────────
COMMENTS_TEMPLATES = [
    "太可爱了！！�?,
    "哈哈哈笑死我�?,
    "感谢分享，很有帮助！",
    "我家的也是这样！",
    "太治愈了，看了心情好多了",
    "有同款！�?,
    "建议去看医生确认一�?,
    "这个我也想知道答�?,
    "感谢科普，学到了",
    "好棒，给你点赞！",
    "这只好像我家的！",
    "第一次看到这种情况，涨知识了",
]

# ── 公告数据 ────────────────────────────────────────────────────────────────
ANNOUNCEMENTS = [
    {
        "title": "🎉 平台上线1周年 | 感谢1000+用户的陪�?,
        "content": "智慧宠物领养平台正式运营满一年！截至目前，已帮助超过300只流浪动物找到了新家，完成智能分诊咨�?000余次，营养方案生�?00+份。感谢每一位用户的信任与支持！",
        "is_hot": 1,
        "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
    },
    {
        "title": "【新功能】AI营养专家上线，支持方案再规划",
        "content": "全新AI营养专家功能正式上线！根据您宠物的具体情况生成个性化营养方案，并支持根据7天反馈进行智能再规划。快�?智能喂养'页面试试吧！",
        "is_hot": 1,
        "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
    },
    {
        "title": "平台使用规范更新说明",
        "content": "为维护社区良好氛围，平台规范进行了更新：1.禁止发布虚假领养信息 2.禁止有偿转让宠物 3.社区帖子需与宠物相关。违规帖子将被删除，严重情况将封禁账号�?,
        "is_hot": 0,
        "date": (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"),
    },
    {
        "title": "【活动�?月领养节，领养费全免",
        "content": "3�?5�?3�?1日，参与本次领养节活动的宠物领养费全部减免！仅需通过资质审核即可领养心仪的毛孩子。名额有限，先到先得�?,
        "is_hot": 1,
        "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    },
    {
        "title": "系统维护通知 | 3�?0日凌�?-4�?,
        "content": "平台将于3�?0日凌�?:00-4:00进行系统维护升级，届时服务将短暂不可用。维护期间产生的数据将在恢复后自动同步。给您带来的不便敬请谅解�?,
        "is_hot": 0,
        "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
    },
]


def seed(clear_existing=False):
    conn = get_db_connection()
    ensure_tables(conn)
    cur = conn.cursor()

    if clear_existing:
        print("  清除现有演示数据...")
        for t in ["announcements", "comments", "posts", "applications", "adopt_records"]:
            cur.execute(f"DELETE FROM {t}")
        # 只保�?个基础账号，清除多余用�?
        cur.execute("DELETE FROM users WHERE id > 3")
        # 重置宠物为初�?�?
        cur.execute("DELETE FROM pets WHERE id > 6")
        conn.commit()

    # ── 1. 用户 ──────────────────────────────────────────────────────────────
    print("填充用户...")
    cur.execute("SELECT email FROM users")
    existing_emails = {r[0] for r in cur.fetchall()}
    for u in USERS:
        if u["email"] not in existing_emails:
            cur.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (u["username"], u["email"], _seed_password(u["password"]), u["role"]),
            )
    conn.commit()

    # 获取用户ID映射
    cur.execute("SELECT id, email FROM users")
    email_to_id = {r["email"]: r["id"] for r in cur.fetchall()}
    user_ids = [email_to_id[u["email"]] for u in USERS]

    # ── 2. 宠物（清空重建，保证30条）────────────────────────────────────────
    print("填充宠物数据�?0条）...")
    cur.execute("DELETE FROM pets")
    for p in PETS:
        owner_uid = user_ids[p["owner_id"] - 1] if p["owner_id"] <= len(user_ids) else user_ids[1]
        cur.execute(
            """INSERT INTO pets (owner_id, name, species, age, is_shedding, energy_level,
               description, image_url, tags, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                owner_uid,
                p["name"], p["species"], p["age"],
                p["is_shedding"], p["energy_level"],
                p["description"], p["image"],
                json.dumps(p.get("tags", []), ensure_ascii=False),
                "待领�?,
            ),
        )
    # 标记几条�?已领�?，让数据更真�?
    conn.commit()
    cur.execute("SELECT id FROM pets LIMIT 4")
    adopted_ids = [r[0] for r in cur.fetchall()]
    for pid in adopted_ids[:2]:
        cur.execute("UPDATE pets SET status='已领�? WHERE id=?", (pid,))
    conn.commit()

    # ── 2.1 为每只宠物填充 pet_features + pet_requirements ───────────────────
    print("填充宠物特征与领养约束...")
    cur.execute("DELETE FROM pet_features")
    cur.execute("DELETE FROM pet_requirements")
    cur.execute("SELECT id, species, age, energy_level, tags FROM pets")
    all_pets = [dict(r) for r in cur.fetchall()]

    _FEATURES_TEMPLATES = [
        {"temperament_tags": "温顺, 安静",   "energy_level": "低",  "social_level": "友好",   "care_level": "容易", "beginner_friendly": 1, "good_with_children": 1, "good_with_other_pets": 1, "budget_need_level": "低", "companionship_need": "低"},
        {"temperament_tags": "粘人, 活泼",   "energy_level": "中",  "social_level": "极其亲人", "care_level": "容易", "beginner_friendly": 1, "good_with_children": 1, "good_with_other_pets": 1, "budget_need_level": "中", "companionship_need": "高"},
        {"temperament_tags": "优雅, 独立",   "energy_level": "低",  "social_level": "孤僻",   "care_level": "困难", "beginner_friendly": 0, "good_with_children": 0, "good_with_other_pets": 0, "budget_need_level": "高", "companionship_need": "低"},
        {"temperament_tags": "好奇, 聪明",   "energy_level": "高",  "social_level": "友好",   "care_level": "中等", "beginner_friendly": 1, "good_with_children": 1, "good_with_other_pets": 1, "budget_need_level": "中", "companionship_need": "中"},
        {"temperament_tags": "温柔, 亲人",   "energy_level": "低",  "social_level": "极其亲人", "care_level": "中等", "beginner_friendly": 1, "good_with_children": 1, "good_with_other_pets": 1, "budget_need_level": "中", "companionship_need": "高"},
        {"temperament_tags": "忠诚, 活泼",   "energy_level": "高",  "social_level": "极其亲人", "care_level": "中等", "beginner_friendly": 1, "good_with_children": 1, "good_with_other_pets": 1, "budget_need_level": "中", "companionship_need": "高"},
        {"temperament_tags": "温顺, 护主",   "energy_level": "中",  "social_level": "友好",   "care_level": "容易", "beginner_friendly": 1, "good_with_children": 1, "good_with_other_pets": 0, "budget_need_level": "高", "companionship_need": "高"},
        {"temperament_tags": "调皮, 精力旺盛", "energy_level": "高", "social_level": "友好",   "care_level": "困难", "beginner_friendly": 0, "good_with_children": 0, "good_with_other_pets": 0, "budget_need_level": "高", "companionship_need": "高"},
    ]

    _REQUIREMENTS_TEMPLATES = [
        {"allow_beginner": 1, "min_budget_level": None, "min_companion_hours": 0,   "forbid_children": 0, "forbid_other_pets": 0, "require_stable_housing": 0, "require_return_visit": 1, "special_notes": None},
        {"allow_beginner": 1, "min_budget_level": "中", "min_companion_hours": 1.0, "forbid_children": 0, "forbid_other_pets": 0, "require_stable_housing": 1, "require_return_visit": 1, "special_notes": "希望领养人有耐心"},
        {"allow_beginner": 0, "min_budget_level": "中", "min_companion_hours": 2.0, "forbid_children": 0, "forbid_other_pets": 0, "require_stable_housing": 1, "require_return_visit": 1, "special_notes": "需要有养宠经验"},
        {"allow_beginner": 0, "min_budget_level": "高", "min_companion_hours": 3.0, "forbid_children": 1, "forbid_other_pets": 1, "require_stable_housing": 1, "require_return_visit": 1, "special_notes": "需安静独居环境，不接受有幼儿家庭"},
    ]

    age_stages = {1: "幼年", 2: "成年", 3: "成年", 4: "成年", 5: "成年", 6: "老年", 7: "老年"}
    genders = ["公", "母"]

    for i, pet in enumerate(all_pets):
        pid = pet["id"]
        spec = "猫" if "猫" in (pet["species"] or "") else "狗"
        ft = _FEATURES_TEMPLATES[i % len(_FEATURES_TEMPLATES)]
        rq = _REQUIREMENTS_TEMPLATES[i % len(_REQUIREMENTS_TEMPLATES)]

        cur.execute(
            """INSERT OR REPLACE INTO pet_features
               (pet_id, species, age_stage, gender, health_status, sterilized,
                energy_level, care_level, beginner_friendly, social_level,
                temperament_tags, good_with_children, good_with_other_pets,
                medical_needs, companionship_need, budget_need_level, special_care_flag)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, spec, age_stages.get(pet["age"], "成年"), genders[i % 2],
                "健康", 1 if i % 3 == 0 else 0,
                ft["energy_level"], ft["care_level"], ft["beginner_friendly"], ft["social_level"],
                ft["temperament_tags"], ft["good_with_children"], ft["good_with_other_pets"],
                None, ft["companionship_need"], ft["budget_need_level"], 0,
            ),
        )

        cur.execute(
            """INSERT OR REPLACE INTO pet_requirements
               (pet_id, allow_beginner, min_budget_level, min_companion_hours,
                required_housing_type, forbid_other_pets, forbid_children,
                require_stable_housing, require_return_visit, special_notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, rq["allow_beginner"], rq["min_budget_level"], rq["min_companion_hours"],
                None, rq["forbid_other_pets"], rq["forbid_children"],
                rq["require_stable_housing"], rq["require_return_visit"], rq["special_notes"],
            ),
        )
    conn.commit()
    print(f"   pet_features: {len(all_pets)} 条")
    print(f"   pet_requirements: {len(all_pets)} 条")

    # ── 3. 公告 ───────────────────────────────────────────────────────────────
    print("填充公告...")
    cur.execute("DELETE FROM announcements")
    for a in ANNOUNCEMENTS:
        cur.execute(
            "INSERT INTO announcements (title, content, is_hot, date) VALUES (?, ?, ?, ?)",
            (a["title"], a["content"], a["is_hot"], a["date"]),
        )
    conn.commit()

    # ── 4. 社区帖子 ───────────────────────────────────────────────────────────
    print("填充社区帖子�?5条）...")
    cur.execute("DELETE FROM posts")
    post_ids = []
    for p in POSTS:
        uid = user_ids[p["user_idx"] - 1] if p["user_idx"] - 1 < len(user_ids) else user_ids[0]
        img = POST_IMAGES[p["image_idx"]] if p.get("image_idx") is not None else None
        create_time = (datetime.now() - timedelta(days=p.get("days_ago", 0))).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO posts (user_id, title, content, image_url, type, likes, create_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uid, p["title"], p["content"], img, p["type"], p["likes"], create_time),
        )
        post_ids.append(cur.lastrowid)
    conn.commit()

    # ── 5. 评论 ───────────────────────────────────────────────────────────────
    print("填充评论...")
    cur.execute("DELETE FROM comments")
    for i, pid in enumerate(post_ids):
        comment_count = random.randint(2, 6)
        for j in range(comment_count):
            uid = random.choice(user_ids)
            content = random.choice(COMMENTS_TEMPLATES)
            create_time = (datetime.now() - timedelta(days=POSTS[i].get("days_ago", 0), hours=random.randint(0, 12))).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO comments (post_id, user_id, content, create_time) VALUES (?, ?, ?, ?)",
                (pid, uid, content, create_time),
            )
    conn.commit()

    # ── 6. 领养申请（模拟几条）───────────────────────────────────────────────
    print("填充领养申请...")
    cur.execute("SELECT id FROM pets WHERE status='待领�? LIMIT 10")
    available_pets = [r[0] for r in cur.fetchall()]
    statuses = ["待审�?, "待审�?, "通过", "通过", "不通过"]
    reasons = [
        "我家有稳定的居住环境，工作时间较固定，每天有足够时间陪伴宠物。已养宠5年，有丰富经验�?,
        "家庭成员都很喜欢动物，有宽敞的客厅和阳台，愿意为宠物提供最好的生活条件�?,
        "单人居住，工作稳定，希望有一个毛茸茸的伙伴陪伴。已提前购置了所有基础物品�?,
        "和另一半都是爱宠人士，有过往领养经历，了解宠物习性，承诺给予终身照料�?,
    ]
    for i, pet_id in enumerate(available_pets[:8]):
        uid = user_ids[i % 4]
        cur.execute(
            "INSERT INTO applications (user_id, pet_id, reason, status) VALUES (?, ?, ?, ?)",
            (uid, pet_id, random.choice(reasons), statuses[i % len(statuses)]),
        )
    conn.commit()
    conn.close()

    print("\n�?种子数据填充完成�?)
    print(f"   用户: {len(USERS)} �?)
    print(f"   宠物: {len(PETS)} 条（�?条已领养�?)
    print(f"   公告: {len(ANNOUNCEMENTS)} �?)
    print(f"   帖子: {len(POSTS)} �?)
    print(f"   评论: ~{len(POSTS) * 4} 条（随机�?)
    print(f"   领养申请: 8 �?)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="填充演示种子数据")
    parser.add_argument("--clear", action="store_true", help="清除已有数据后重新填�?)
    args = parser.parse_args()
    seed(clear_existing=args.clear)
