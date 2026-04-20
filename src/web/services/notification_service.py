import logging
import os
from datetime import datetime
from pathlib import Path

# 设置通知日志路径
LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
NOTIF_LOG = LOG_DIR / "notifications.log"

class NotificationService:
    @staticmethod
    def send_adoption_result(
        applicant_email: str,
        applicant_name: str,
        pet_name: str,
        status: str,  # 'approved' or 'rejected'
        owner_name: str,
        owner_contact: str,
        owner_note: str = "",
        ai_risk_summary: str = ""
    ):
        """模拟发送审核结果通知邮件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = f"【智慧领养系统】关于您对宠物“{pet_name}”的领养申请结果通知"
        
        if status == 'approved':
            content = (
                f"亲爱的 {applicant_name} ({applicant_email})：\n\n"
                f"恭喜您！您发起的对宠物“{pet_name}”的领养申请已通过审核。\n"
                f"送养人“{owner_name}”对您的申请表示认可。\n\n"
                f"--- 送养人联系方式 ---\n"
                f"联系邮箱/电话：{owner_contact}\n"
                f"送养人寄语：{owner_note if owner_note else '无'}\n\n"
                f"请您尽快在系统中确认“接宠物回家”，并与送养人取得联系沟通线下交付事宜。\n"
            )
        else:
            content = (
                f"亲爱的 {applicant_name} ({applicant_email})：\n\n"
                f"很抱歉地通知您，您对宠物“{pet_name}”的领养申请未能通过本次审核。\n\n"
                f"--- 审核反馈 ---\n"
                f"送养人说明：{owner_note if owner_note else '未提供具体说明'}\n"
                f"AI 审计风险点提示：{ai_risk_summary if ai_risk_summary else '匹配度评分较低'}\n\n"
                f"领养是一项长期的责任，建议您根据反馈完善个人画像，或关注其他更适合您的宠物。感谢您对流浪动物的关注！\n"
            )

        log_entry = (
            f"\n{'='*60}\n"
            f"发送时间: {timestamp}\n"
            f"收件人: {applicant_email}\n"
            f"主题: {subject}\n"
            f"内容:\n{content}"
            f"{'='*60}\n"
        )

        with open(NOTIF_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # 同时打印到后台控制台，方便演示观察
        print(f"\n[Notification] 模拟邮件已发送至 {applicant_email}")
        print(f"[Subject] {subject}")
        return True
