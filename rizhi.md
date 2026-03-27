建议新增 5 个接口
1. 启动评估

POST /api/adoption/evaluate/{application_id}

作用：启动 Flow，而不是直接同步生成结论。

2. 获取评估状态

GET /api/adoption/evaluate/{application_id}/status

作用：前端轮询或刷新查看当前在“预筛/专家评估/待补充/待审核/已完成”哪个状态。

3. 提交补充信息

POST /api/adoption/evaluate/{application_id}/followup

作用：Flow 在 need_more_info 时，把新信息再送入下一轮评估。

4. 人工反馈

POST /api/adoption/evaluate/{application_id}/review

作用：发布者或管理员提交“通过/拒绝/继续追问/人工复核”。

5. 写回回访

POST /api/adoption/evaluate/{application_id}/feedback

作用：把领养后回访写入 memory 或案例库。

这样前端层面只多了“状态查询”和“补充/审核”两个交互，不算大改。