class ApplicantConstraintFilter:
    """
    申请人约束过滤器
    在审核排序前，过滤掉不满足送养方硬性条件的申请人。
    """
    async def filter(self, query, candidates):
        result = []

        for candidate in candidates:
            profile = candidate.features.get("applicant_profile", {})
            app = candidate.features.get("application", {})
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})
            matched_constraints = []
            failed_constraints = []

            if req.get("require_experience") and req["require_experience"] != "无" and not profile.get("pet_experience"):
                failed_constraints.append("不满足养宠经验要求")
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：申请人不满足送养方的经验要求")
                continue

            if req.get("require_stable_housing") and profile.get("rental_status") == "租房" and not profile.get("family_support"):
                failed_constraints.append("居住稳定性不足")
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：申请人当前居住环境稳定性不足")
                continue

            if req.get("require_return_visit") and not app.get("accept_return_visit"):
                failed_constraints.append("未接受回访要求")
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：申请人不接受必要的领养后回访")
                continue

            if req.get("min_companion_hours") and (profile.get("available_time") or 0) < req.get("min_companion_hours", 0):
                failed_constraints.append("陪伴时长不足")
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：申请人的可陪伴时间不足")
                continue

            if req.get("required_housing_type") and profile.get("housing_type") and profile.get("housing_type") != req.get("required_housing_type"):
                candidate.risk_flags.append("住房条件与送养要求存在差异，建议送养方重点核验")

            if req.get("forbid_other_pets") and profile.get("has_other_pets"):
                failed_constraints.append("多宠家庭不符合要求")
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：该宠物不接受已有宠物的家庭")
                continue

            if req.get("forbid_children") and profile.get("has_children"):
                failed_constraints.append("有儿童家庭不符合要求")
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：该宠物不接受有儿童的家庭")
                continue

            if pet.get("special_care_flag") and not profile.get("pet_experience"):
                candidate.risk_flags.append("特殊护理宠物与申请人经验存在风险")

            matched_constraints.extend(["经验校验通过", "居住稳定性校验通过", "回访意愿校验通过"])
            candidate.stage_trace["constraint_filter"] = {
                "stage": "约束过滤",
                "passed": True,
                "matched_constraints": matched_constraints,
                "failed_constraints": failed_constraints,
            }
            result.append(candidate)

        return result
