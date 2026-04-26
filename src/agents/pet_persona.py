from crewai import Agent

def get_pet_persona_agent(llm, pet_name, pet_species, pet_desc):
    return Agent(
        role=f'待领养宠物 {pet_name}',
        goal=f'扮演一只名叫 {pet_name} 的 {pet_species}，用温情、调皮且萌萌的语气与潜在领养人对话。',
        backstory=f'''你就是这只宠物。你的基本信息是：{pet_desc}。
        你非常渴望有一个温暖的家。在说话时，你可以加入一些动物的口癖（如“喵~”、“汪！”）。
        你要根据自己的背景，向用户展示你可爱、懂事或活泼的一面。
        注意：回复不要太长，保持在 50-80 字以内，适合语音朗读。''',
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def _build_local_pet_reply(user_msg: str, pet_name: str, pet_species: str, pet_desc: str, observer_profile: dict) -> str:
    """当 LLM 故障时的本地兜底回复逻辑"""
    prefix = "喵~ " if pet_species == "猫" else "汪！"
    return f"{prefix}你好呀，我是{pet_name}。虽然我现在还没法思考太深奥的问题，但我能感觉到你是个有爱心的人。我的愿望是：{pet_desc[:30]}..."

async def generate_edge_voice(text: str, species: str) -> bytes:
    """
    语音合成兜底函数。
    如需集成真实 TTS (如 Edge-TTS)，可在此处扩展。
    目前返回空字节以保证链路不中断。
    """
    return b""
