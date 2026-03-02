import os
import sys
# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.agents.agents import run_pet_crew
except ImportError:
    from agents.agents import run_pet_crew

def test():
    print("🚀 开始多智能体流程测试...")
    user_input = "我想领养一只安静的猫，适合在公寓养。另外，猫如果不吃东西怎么办？"
    
    try:
        response = run_pet_crew(user_input)
        print("\n" + "="*30)
        print("🤖 AI 最终回复：")
        print(response)
        print("="*30)
    except Exception as e:
        print(f"❌ 测试失败：{e}")

if __name__ == "__main__":
    test()
