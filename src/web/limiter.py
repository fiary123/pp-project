from slowapi import Limiter
from slowapi.util import get_remote_address

# 全局限速器实例（独立模块，避免循环导入）
# 移除过时的 app 参数，由 app.py 通过 state 机制或中间件统一挂载
limiter = Limiter(key_func=get_remote_address)
