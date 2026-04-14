class ApplicantConstraintFilter:
    """
    申请人约束过滤器 - 增强演示版
    用于审核排序场景，在评分前过滤掉明显不符合送养方硬性要求的申请人。
    """
    async def filter(self, query, candidates):
        res, _ = await self.filter_with_details(query, candidates)
        return res

    async def filter_with_details(self, query, candidates):
        result = []
        intercepted = []
        # 在此场景下，query.pet_id 是目标，candidates 是申请人
        
        for candidate in candidates:
            profile = candidate.features.get("applicant_profile", {})
            # app = candidate.features.get("application", {})
            # pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            # 1. 经验要求
            if not req.get("allow_beginner") and profile.get("experience_level", 0) == 0:
                intercepted.append({
                    "id": candidate.candidate_id,
                    "name": profile.get("username", "申请人"),
                    "reason": "硬性准入过滤：送养方要求必须有养宠经验，申请人为新手"
                })
                continue

            # 2. 陪伴时间
            if float(profile.get("available_time", 0)) < float(req.get("min_companion_hours", 0)):
                intercepted.append({
                    "id": candidate.candidate_id,
                    "name": profile.get("username", "申请人"),
                    "reason": f"照护能力过滤：申请人每日陪伴时间({profile.get('available_time')}h)不足({req.get('min_companion_hours')}h)"
                })
                continue

            # 3. 住房稳定性
            if req.get("require_stable_housing") and profile.get("rental_status") == "租房":
                # 这里通常只是增加风险标签，但如果要求极严则过滤
                pass

            result.append(candidate)

        return result, intercepted
