import os

file_path = 'src/web/routers/ai.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 统一审计相关的角色检查
content = content.replace('current_user.get("role") != "admin"', 'current_user.get("role") not in ["org_admin", "root_admin"]')
content = content.replace('current_user.get("role") not in ["admin"]', 'current_user.get("role") not in ["org_admin", "root_admin"]')

# 统一 _ensure_application_access 中的逻辑
content = content.replace('current_user.get("role") == "admin"', 'current_user.get("role") in ["org_admin", "root_admin"]')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("ai.py roles synchronized.")
