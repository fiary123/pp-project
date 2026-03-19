from slowapi import Limiter
from slowapi.util import get_remote_address

# 全局限速器实例（独立模块，避免循环导入）
limiter = Limiter(key_func=get_remote_address)
