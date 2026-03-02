# FastAPI 后端接口服务
import os
import sys
# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
try:
    from src.agents.agents import run_pet_crew
except ImportError:
    from ..agents.agents import run_pet_crew
import uvicorn

app = FastAPI(title="智能宠物领养平台 API")

# 允许跨域请求（让前端能连上后端）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    try:
        print(f"收到用户消息: {request.message}")
        # 唤醒多智能体团队进行处理
        ai_response = run_pet_crew(request.message)
        return {"status": "success", "reply": ai_response}
    except Exception as e:
        return {"status": "error", "reply": f"系统大脑开小差了: {str(e)}"}

if __name__ == "__main__":
    print("🚀 AI 后端服务启动于 http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)