import os

files = ['src/web/routers/admin.py', 'src/web/routers/ai.py']
for fp in files:
    if not os.path.exists(fp): continue
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 彻底恢复到两级权限
    content = content.replace('from src.web.dependencies import require_org_admin', 'from src.web.dependencies import require_admin')
    content = content.replace('Depends(require_org_admin)', 'Depends(require_admin)')
    content = content.replace('current_user.get("role") not in ["org_admin", "root_admin"]', 'current_user.get("role") != "admin"')
    content = content.replace('current_user.get("role") in ["org_admin", "root_admin"]', 'current_user.get("role") == "admin"')

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
print("Simplified roles applied to backend.")
