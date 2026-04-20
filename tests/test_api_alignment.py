import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from src.web.app import app


client = TestClient(app)


def test_register_and_login_flow():
    email = 'new_user_for_test@example.com'
    register = client.post('/api/register', json={
        'username': '测试用户',
        'email': email,
        'password': '123456',
        'role': 'user'
    })
    assert register.status_code in (200, 400)

    login = client.post('/api/login', json={'email': email, 'password': '123456'})
    assert login.status_code == 200
    body = login.json()
    assert body['status'] == 'success'
    assert 'user' in body


def test_frontend_missing_endpoints_now_available():
    chat = client.post('/api/chat', json={'message': '猫咪不吃饭怎么办？'})
    assert chat.status_code == 200
    assert 'reply' in chat.json()

    messages = client.get('/api/messages/1')
    assert messages.status_code == 200
    assert isinstance(messages.json(), list)


def test_admin_and_community_endpoints():
    send_msg = client.post('/api/messages/send', json={'sender_id': 1, 'receiver_id': 2, 'content': '你好'})
    assert send_msg.status_code == 200

    like = client.post('/api/posts/1/like')
    assert like.status_code == 200

    comment = client.post('/api/posts/comment', json={'post_id': 1, 'user_id': 1, 'content': '测试评论'})
    assert comment.status_code == 200

    admin_users = client.get('/api/admin/users')
    assert admin_users.status_code == 200

    admin_apps = client.get('/api/admin/applications')
    assert admin_apps.status_code == 200
