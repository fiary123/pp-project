import time
import statistics
import json
from tests.eval_dataset import get_expanded_dataset
from src.web.services.ai_service import generate_nutrition_plan, get_triage_reply

def mock_rule_engine_triage(symptom: str):
    """模拟传统 A 系统：简单的关键词匹配逻辑"""
    if any(k in symptom for k in ["不吃", "吐", "拉稀", "没精神"]):
        return "建议就医：观察到消化道症状"
    return "一般性建议：暂无严重异常"

def mock_rule_engine_nutrition(data: dict):
    """模拟传统 A 系统：固定的 RER 计算公式"""
    kcal = 70 * (data["weight_kg"] ** 0.75) * 1.6 # 简单的固定系数
    return {"daily_kcal": round(kcal, 2)}

def run_evaluation():
    nutrition_cases, triage_cases = get_expanded_dataset()
    results = {
        "Rule_System_A": {"latency": [], "completion": [], "risk_coverage": 0},
        "Agent_System_B": {"latency": [], "completion": [], "risk_coverage": 0}
    }

    # 1. 评估分诊系统
    for case in triage_cases:
        # A 系统
        start = time.time()
        _ = mock_rule_engine_triage(case["symptom"])
        results["Rule_System_A"]["latency"].append((time.time() - start) * 1000)

        # B 系统
        start = time.time()
        reply, _ = get_triage_reply(case["symptom"])
        results["Agent_System_B"]["latency"].append((time.time() - start) * 1000)
        
        # 风险覆盖率检查 (简单模拟)
        if "expected_risk" in case and "建议" in reply:
             results["Agent_System_B"]["risk_coverage"] += 1

    # 2. 评估营养系统
    for case in nutrition_cases:
        # 复制数据并移除 build_nutrition_plan 不支持的 desc 字段
        eval_case = case.copy()
        eval_case.pop("desc", None)

        # A 系统
        res_a = mock_rule_engine_nutrition(eval_case)
        results["Rule_System_A"]["completion"].append(1 if "daily_kcal" in res_a else 0)

        # B 系统
        res_b, _, _, _ = generate_nutrition_plan({**eval_case, "user_id": 0, "pet_name": "EvalPet"})
        # 检查结构化字段完整率 (核心论文指标)
        fields = ["daily_kcal", "water_ml", "confidence_level", "recheck_in_days"]
        completion_score = sum(1 for f in fields if f in res_b) / len(fields)
        results["Agent_System_B"]["completion"].append(completion_score)

    # 汇总
    summary = {}
    for system in results:
        summary[system] = {
            "avg_latency_ms": round(statistics.mean(results[system]["latency"]), 2) if results[system]["latency"] else 0.5,
            "avg_completion_rate": round(statistics.mean(results[system]["completion"]) * 100, 2),
            "risk_alert_coverage": f"{results[system]['risk_coverage']/len(triage_cases)*100}%"
        }
    
    with open("docs/EVALUATION_SUMMARY.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    
    return summary

if __name__ == "__main__":
    print("🚀 启动数据与评估实验...")
    report = run_evaluation()
    print("📊 评估报告生成完毕:", report)
