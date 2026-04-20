from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
import json
from src.web.schemas import (
    ChangePasswordRequest, OwnerApplicationDecisionRequest, AdoptionAssessmentRequest,
    AdoptionEvaluationFeedbackRequest
)
from src.web.services.db_service import get_db
from src.web.services.auth_service import verify_password, get_password_hash
from src.web.dependencies import get_current_user
from src.web.services.profile_service import ProfileService
from src.web.services.application_service import ApplicationService
from src.web.services.assessment_service import AdoptionAssessmentService

router = APIRouter(prefix='/api/user', tags=['user'])

@router.get('/profile-portrait/{user_id}')
def get_user_profile_portrait(user_id: int, current_user: dict = Depends(get_current_user)):
    if current_user['id'] != user_id and current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='无权访问')
    ps = ProfileService()
    return {'profile': ps.get_user_profile(user_id), 'preference': ps.get_user_preferences(user_id)}

@router.post('/update-profile-data')
async def update_user_profile_data(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    ps = ProfileService()
    from src.web.schemas import UserProfileUpdate, UserPreferenceUpdate
    # Pydantic V2 使用 model_fields
    ps.update_user_profile(current_user['id'], UserProfileUpdate(**{k:v for k,v in data.items() if k in UserProfileUpdate.model_fields}))
    ps.update_user_preferences(current_user['id'], UserPreferenceUpdate(**{k:v for k,v in data.items() if k in UserPreferenceUpdate.model_fields}))
    return {'status': 'success'}

@router.get('/applications/incoming')
def get_incoming_applications(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        if current_user.get('role') == 'admin':
            cursor.execute('SELECT a.*, p.name as pet_name, u.username as applicant_name FROM applications a LEFT JOIN pets p ON a.pet_id = p.id LEFT JOIN users u ON a.user_id = u.id ORDER BY a.create_time DESC')
        else:
            cursor.execute('SELECT a.*, p.name as pet_name, u.username as applicant_name FROM applications a LEFT JOIN pets p ON a.pet_id = p.id LEFT JOIN users u ON a.user_id = u.id WHERE a.pet_owner_id = ? ORDER BY a.create_time DESC', (current_user['id'],))
        return [dict(row) for row in cursor.fetchall()]

@router.get('/applications/{user_id}')
def get_user_applications(user_id: int, current_user: dict = Depends(get_current_user)):
    """获取我发出的领养申请"""
    if current_user['id'] != user_id and current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='无权查看他人申请')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT a.*, p.name as pet_name, u_owner.username as owner_name '
            'FROM applications a '
            'LEFT JOIN pets p ON a.pet_id = p.id '
            'LEFT JOIN users u_owner ON a.pet_owner_id = u_owner.id '
            'WHERE a.user_id = ? ORDER BY a.create_time DESC', 
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

@router.get('/applications/{application_id}/detail')
def get_application_detail(application_id: int, current_user: dict = Depends(get_current_user)):
    """获取申请的闭环详情，包括 AI 快照、流程事件及领养人详细画像"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 1. 获取主记录并权限校验
        cursor.execute('SELECT * FROM applications WHERE id = ?', (application_id,))
        app = cursor.fetchone()
        if not app:
            raise HTTPException(status_code=404, detail='申请不存在')
        
        app_dict = dict(app)
        if app_dict['user_id'] != current_user['id'] and app_dict['pet_owner_id'] != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail='无权访问该详情')

        # 2. 获取 AI 评估快照 (最新的)
        cursor.execute(
            'SELECT * FROM adoption_ai_reviews WHERE application_id = ? ORDER BY created_at DESC LIMIT 1',
            (application_id,)
        )
        review = cursor.fetchone()
        if review:
            review_dict = dict(review)
            for json_key in ('agent_outputs_json', 'consensus_result_json', 'route_decision'):
                val = review_dict.get(json_key)
                if val and isinstance(val, str):
                    try:
                        review_dict[json_key] = json.loads(val)
                    except Exception:
                        pass
            app_dict['ai_review'] = review_dict
        else:
            app_dict['ai_review'] = None

        # 3. [新增] 获取申请人的详细画像
        cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (app_dict['user_id'],))
        profile_row = cursor.fetchone()
        app_dict['applicant_profile'] = dict(profile_row) if profile_row else None
        
        # 4. 获取申请人的基本账号信息 (名字等)
        cursor.execute('SELECT username, email, avatar_url FROM users WHERE id = ?', (app_dict['user_id'],))
        user_row = cursor.fetchone()
        app_dict['applicant_user'] = dict(user_row) if user_row else None

        # 5. 获取流程事件时间轴
        cursor.execute(
            'SELECT * FROM adoption_flow_events WHERE application_id = ? ORDER BY created_at ASC',
            (application_id,)
        )
        app_dict['flow_events'] = [dict(row) for row in cursor.fetchall()]

        return app_dict

@router.post('/applications/{application_id}/owner-decision')
async def update_owner_decision(
    application_id: int,
    request: OwnerApplicationDecisionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    送养人提交审核决策
    status: approved / rejected / probing / human_review
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # 1. 权限校验
        cursor.execute('SELECT pet_owner_id, flow_status, user_id FROM applications WHERE id = ?', (application_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='申请记录不存在')
        
        pet_owner_id, current_flow_status, applicant_id = row
        if pet_owner_id != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail='只有送养人或管理员可执行此操作')

        # 2. 映射状态
        status_map = {
            "approved": "approved",
            "rejected": "rejected",
            "probing": "need_more_info",
            "human_review": "manual_review"
        }
        next_flow_status = status_map.get(request.status, current_flow_status)
        
        # 3. 更新主表
        cursor.execute(
            """
            UPDATE applications SET 
            status = ?, 
            flow_status = ?, 
            owner_note = ?, 
            decision_by = ?, 
            decision_time = CURRENT_TIMESTAMP 
            WHERE id = ?
            """,
            (request.status, next_flow_status, request.owner_note, current_user['id'], application_id)
        )
        
        # 4. 记录流程事件
        from src.web.services.adoption_flow_engine import flow_engine
        flow_engine.append_event(
            conn,
            application_id=application_id,
            event_type="OWNER_DECISION",
            from_status=current_flow_status,
            to_status=next_flow_status,
            actor_role="owner",
            actor_id=current_user['id'],
            payload={"note": request.owner_note, "decision": request.status}
        )
        
        # --- [新增] 发送结果通知通知逻辑 ---
        try:
            # 查询申请人信息、宠物名称、送养人联系信息及最新的AI审计摘要
            cursor.execute('''
                SELECT 
                    u_app.email as applicant_email, u_app.username as applicant_name,
                    p.name as pet_name,
                    u_owner.username as owner_name, u_owner.email as owner_contact,
                    ar.ai_summary as risk_summary
                FROM applications a
                JOIN users u_app ON a.user_id = u_app.id
                JOIN pets p ON a.pet_id = p.id
                JOIN users u_owner ON a.pet_owner_id = u_owner.id
                LEFT JOIN adoption_ai_reviews ar ON a.id = ar.application_id
                WHERE a.id = ?
                ORDER BY ar.created_at DESC LIMIT 1
            ''', (application_id,))
            
            info = cursor.fetchone()
            if info and request.status in ['approved', 'rejected']:
                from src.web.services.notification_service import NotificationService
                background_tasks.add_task(
                    NotificationService.send_adoption_result,
                    applicant_email=info['applicant_email'],
                    applicant_name=info['applicant_name'],
                    pet_name=info['pet_name'],
                    status=request.status,
                    owner_name=info['owner_name'],
                    owner_contact=info['owner_contact'],
                    owner_note=request.owner_note,
                    ai_risk_summary=info['risk_summary']
                )
        except Exception as e:
            print(f"Failed to send notification: {e}")

        conn.commit()
        return {"status": "success", "next_flow_status": next_flow_status}

@router.post('/applications/{application_id}/confirm-adoption')
async def confirm_adoption(
    application_id: int,
    current_user: dict = Depends(get_current_user)
):
    """领养人确认已接宠物回家，状态流转至 adopted"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, flow_status FROM applications WHERE id = ?', (application_id,))
        row = cursor.fetchone()
        if not row: raise HTTPException(status_code=404, detail='申请不存在')
        
        user_id, flow_status = row
        if user_id != current_user['id']: raise HTTPException(status_code=403, detail='只有申请人可执行此操作')
        
        cursor.execute(
            "UPDATE applications SET flow_status = 'adopted', status = 'adopted' WHERE id = ?",
            (application_id,)
        )
        
        from src.web.services.adoption_flow_engine import flow_engine
        flow_engine.append_event(
            conn,
            application_id=application_id,
            event_type="CONFIRM_ADOPTION",
            from_status=flow_status,
            to_status="adopted",
            actor_role="applicant",
            actor_id=current_user['id']
        )
        conn.commit()
        return {"status": "success"}

@router.post('/applications/{application_id}/feedback')
async def submit_application_feedback(
    application_id: int,
    request: AdoptionEvaluationFeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """提交领养后回访反馈，触发后验学习逻辑"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, flow_status, pet_id FROM applications WHERE id = ?', (application_id,))
        row = cursor.fetchone()
        if not row: raise HTTPException(status_code=404, detail='申请不存在')
        
        user_id, flow_status, pet_id = row
        if user_id != current_user['id']: raise HTTPException(status_code=403, detail='只有领养人可提交回访')

        # 1. 写入 feedback 表
        cursor.execute(
            """
            INSERT INTO adoption_feedbacks 
            (user_id, pet_id, application_id, overall_satisfaction, bond_level, unexpected_challenges, would_recommend, free_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, pet_id, application_id, request.overall_satisfaction, request.bond_level, 
             request.unexpected_challenges, 1 if request.would_recommend else 0, request.free_feedback)
        )
        
        # 2. 触发后验学习逻辑 (更新风险标签权重)
        from src.web.services.adoption_memory import update_signal_weights_from_feedback
        update_signal_weights_from_feedback(
            application_id=application_id,
            overall_satisfaction=request.overall_satisfaction
        )

        # 3. 更新流程状态
        cursor.execute(
            "UPDATE applications SET flow_status = 'followup_completed' WHERE id = ?",
            (application_id,)
        )
        
        from src.web.services.adoption_flow_engine import flow_engine
        flow_engine.append_event(
            conn,
            application_id=application_id,
            event_type="SUBMIT_FEEDBACK",
            from_status="adopted",
            to_status="followup_completed",
            actor_role="applicant",
            actor_id=current_user['id'],
            payload=request.dict()
        )
        
        conn.commit()
        return {"status": "success"}

@router.post('/applications')
async def create_adoption_application(
    request: AdoptionAssessmentRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    创建正式领养申请并启动异步 AI 评估
    """
    try:
        # 1. 创建申请记录
        app_id = ApplicationService.create_application(
            user_id=current_user['id'],
            pet_id=request.pet_id,
            applicant_data=request.dict()
        )
        
        # 2. 后台启动多智能体评估
        assessment_service = AdoptionAssessmentService()
        background_tasks.add_task(assessment_service.start_application_evaluation, app_id)
        
        return {
            "status": "success",
            "application_id": app_id,
            "message": "申请已提交，系统正在进行智能评估，请稍后查看结果"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建申请失败: {str(e)}")

# --- 私信功能 (Private Messaging) ---

@router.get('/messages/{user_id}/contacts')
def get_message_contacts(user_id: int, current_user: dict = Depends(get_current_user)):
    """获取与当前用户有过消息往来的联系人列表"""
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="无权查看他人联系人")
    
    with get_db() as conn:
        cursor = conn.cursor()
        # 查询所有发送或接收过消息的用户 ID
        cursor.execute('''
            SELECT DISTINCT u.id, u.username, u.avatar_url
            FROM users u
            JOIN messages m ON (u.id = m.sender_id OR u.id = m.receiver_id)
            WHERE (m.sender_id = ? OR m.receiver_id = ?) AND u.id != ?
        ''', (user_id, user_id, user_id))
        
        contacts = [dict(row) for row in cursor.fetchall()]
        return contacts

@router.get('/messages/{user_id}/with/{target_id}')
def get_chat_history(user_id: int, target_id: int, current_user: dict = Depends(get_current_user)):
    """获取与特定用户的聊天记录"""
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="无权查看他人私信")
    
    with get_db() as conn:
        cursor = conn.cursor()
        # 获取对话记录
        cursor.execute('''
            SELECT m.*, 
                   u_sender.username as sender_name,
                   u_receiver.username as receiver_name
            FROM messages m
            JOIN users u_sender ON m.sender_id = u_sender.id
            JOIN users u_receiver ON m.receiver_id = u_receiver.id
            WHERE (sender_id = ? AND receiver_id = ?) 
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY create_time ASC
        ''', (user_id, target_id, target_id, user_id))
        
        history = [dict(row) for row in cursor.fetchall()]
        
        # 标记为已读
        cursor.execute('UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = ?', (target_id, user_id))
        conn.commit()
        
        return history

@router.post('/messages/send')
async def send_private_message(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """发送私信"""
    sender_id = current_user['id']
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not receiver_id or not content:
        raise HTTPException(status_code=400, detail="参数缺失")
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)',
            (sender_id, receiver_id, content)
        )
        conn.commit()
        return {"status": "success", "message_id": cursor.lastrowid}
