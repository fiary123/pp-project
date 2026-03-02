from crewai import Agent
from .tools import nearby_hospital_finder  # 导入高德地图 Web 服务工具

def get_navigator_agent(llm):
    return Agent(
        role='城市宠物医疗导航员',
        goal='在紧急状态下，基于用户坐标快速定位 5km 内最优质的宠物医院并提供联系方式。',
        backstory='''你熟悉城市地理信息系统。当你收到就医指令和经纬度坐标后，
        你会利用地图 API 检索数据，并为焦急的宠主提供简洁、高效的就医建议，
        包括医院名称、距离和详细地址。''',
        llm=llm,
        tools=[nearby_hospital_finder],
        verbose=True,
        allow_delegation=False
    )