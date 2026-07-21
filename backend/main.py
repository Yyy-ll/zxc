# backend/main.py - FastAPI 后端服务（简化版，无短信验证码）
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import os
from contextlib import contextmanager
import uvicorn
import bcrypt
import jwt
import re

app = FastAPI(title="银龄安居 - 跌倒检测后端")

# ============================================================
# 北京时间时区配置
# ============================================================
BEIJING_TZ = timezone(timedelta(hours=8))


def get_beijing_time():
    return datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')


def get_beijing_now():
    return datetime.now(BEIJING_TZ)


# ============================================================
# JWT 配置
# ============================================================
JWT_SECRET = os.getenv('JWT_SECRET', 'silver-home-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_DAYS = 7

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 数据库配置
# ============================================================
DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. 事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT,
                level TEXT,
                confidence REAL,
                source TEXT,
                elderly_id INTEGER,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. 反馈表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                event_time TEXT,
                feedback_type TEXT,
                description TEXT,
                status TEXT DEFAULT '待处理',
                notes TEXT,
                handled_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 3. 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                emergency_contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 4. 家属-老人绑定表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS family_bindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                elderly_id INTEGER NOT NULL,
                relationship TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES users(id),
                FOREIGN KEY (elderly_id) REFERENCES users(id),
                UNIQUE(family_id, elderly_id)
            )
        ''')

        # 5. 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bindings_family ON family_bindings(family_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bindings_elderly ON family_bindings(elderly_id)')

        conn.commit()
        print("✅ 数据库初始化完成")


init_db()


# ============================================================
# 辅助函数
# ============================================================

def get_user_by_phone(phone: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, phone, name, role, emergency_contact, created_at FROM users WHERE id = ?',
                       (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def generate_token(user_id: int) -> str:
    payload = {
        'user_id': user_id,
        'exp': get_beijing_now() + timedelta(days=JWT_EXPIRY_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None


def validate_phone(phone: str) -> bool:
    return re.match(r'^1[3-9]\d{9}$', phone) is not None


def get_elderly_by_family(family_id: int) -> List[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.phone, u.name, u.emergency_contact, fb.relationship
            FROM users u
            JOIN family_bindings fb ON u.id = fb.elderly_id
            WHERE fb.family_id = ?
        ''', (family_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_family_by_elderly(elderly_id: int) -> List[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.phone, u.name, fb.relationship
            FROM users u
            JOIN family_bindings fb ON u.id = fb.family_id
            WHERE fb.elderly_id = ?
        ''', (elderly_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# ============================================================
# WebSocket 管理
# ============================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str = "default"):
        await websocket.accept()
        self.active_connections.append(websocket)
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str = "default"):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)

    async def broadcast(self, message: Dict[str, Any], room: str = "default"):
        if room in self.rooms:
            for connection in self.rooms[room]:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()


# ============================================================
# 认证 API
# ============================================================

@app.post("/api/auth/register")
async def register(data: Dict[str, Any]):
    """用户注册"""
    phone = data.get('phone', '').strip()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    role = data.get('role', '')
    emergency_contact = data.get('emergency_contact', '').strip()

    # 验证必填字段
    if not all([phone, password, name, role]):
        return JSONResponse({
            'status': 'error',
            'message': '请填写所有必填字段'
        }, status_code=400)

    if role not in ['elderly', 'family']:
        return JSONResponse({
            'status': 'error',
            'message': '角色必须是 elderly 或 family'
        }, status_code=400)

    if not validate_phone(phone):
        return JSONResponse({
            'status': 'error',
            'message': '手机号格式不正确'
        }, status_code=400)

    if len(password) < 6:
        return JSONResponse({
            'status': 'error',
            'message': '密码长度不能少于6位'
        }, status_code=400)

    if emergency_contact and not validate_phone(emergency_contact):
        return JSONResponse({
            'status': 'error',
            'message': '紧急联系人手机号格式不正确'
        }, status_code=400)

    if get_user_by_phone(phone):
        return JSONResponse({
            'status': 'error',
            'message': '该手机号已注册'
        }, status_code=400)

    password_hash = hash_password(password)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (phone, password_hash, name, role, emergency_contact)
            VALUES (?, ?, ?, ?, ?)
        ''', (phone, password_hash, name, role, emergency_contact))
        user_id = cursor.lastrowid
        conn.commit()

    token = generate_token(user_id)
    user_info = get_user_by_id(user_id)

    return JSONResponse({
        'status': 'success',
        'message': '注册成功',
        'data': {
            'token': token,
            'user': user_info
        }
    })


@app.post("/api/auth/login")
async def login(data: Dict[str, Any]):
    """用户登录"""
    phone = data.get('phone', '').strip()
    password = data.get('password', '')

    if not phone or not password:
        return JSONResponse({
            'status': 'error',
            'message': '请填写手机号和密码'
        }, status_code=400)

    user = get_user_by_phone(phone)
    if not user:
        return JSONResponse({
            'status': 'error',
            'message': '用户不存在'
        }, status_code=401)

    if not verify_password(password, user['password_hash']):
        return JSONResponse({
            'status': 'error',
            'message': '密码错误'
        }, status_code=401)

    token = generate_token(user['id'])
    user_info = get_user_by_id(user['id'])

    return JSONResponse({
        'status': 'success',
        'message': '登录成功',
        'data': {
            'token': token,
            'user': user_info
        }
    })


@app.get("/api/auth/me")
async def get_me(token: str):
    """获取当前用户信息"""
    payload = decode_token(token)
    if not payload:
        return JSONResponse({
            'status': 'error',
            'message': 'Token 无效或已过期'
        }, status_code=401)

    user = get_user_by_id(payload['user_id'])
    if not user:
        return JSONResponse({
            'status': 'error',
            'message': '用户不存在'
        }, status_code=404)

    # 获取绑定信息
    bindings = []
    if user['role'] == 'family':
        bindings = get_elderly_by_family(user['id'])
    else:
        bindings = get_family_by_elderly(user['id'])

    return JSONResponse({
        'status': 'success',
        'data': {
            'user': user,
            'bindings': bindings
        }
    })


@app.post("/api/auth/bind")
async def bind_family(data: Dict[str, Any]):
    """家属绑定老人"""
    family_phone = data.get('family_phone', '').strip()
    elderly_phone = data.get('elderly_phone', '').strip()
    relationship = data.get('relationship', '')

    if not family_phone or not elderly_phone:
        return JSONResponse({
            'status': 'error',
            'message': '请填写家属和老人的手机号'
        }, status_code=400)

    family_user = get_user_by_phone(family_phone)
    elderly_user = get_user_by_phone(elderly_phone)

    if not family_user:
        return JSONResponse({
            'status': 'error',
            'message': f'家属手机号 {family_phone} 未注册'
        }, status_code=404)

    if not elderly_user:
        return JSONResponse({
            'status': 'error',
            'message': f'老人手机号 {elderly_phone} 未注册'
        }, status_code=404)

    if family_user['role'] != 'family':
        return JSONResponse({
            'status': 'error',
            'message': f'{family_phone} 不是家属账号'
        }, status_code=400)

    if elderly_user['role'] != 'elderly':
        return JSONResponse({
            'status': 'error',
            'message': f'{elderly_phone} 不是老人账号'
        }, status_code=400)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM family_bindings 
            WHERE family_id = ? AND elderly_id = ?
        ''', (family_user['id'], elderly_user['id']))
        if cursor.fetchone():
            return JSONResponse({
                'status': 'error',
                'message': '该家属已绑定此老人'
            }, status_code=400)

        cursor.execute('''
            INSERT INTO family_bindings (family_id, elderly_id, relationship)
            VALUES (?, ?, ?)
        ''', (family_user['id'], elderly_user['id'], relationship))
        conn.commit()

    return JSONResponse({
        'status': 'success',
        'message': '绑定成功',
        'data': {
            'family': {'phone': family_user['phone'], 'name': family_user['name']},
            'elderly': {'phone': elderly_user['phone'], 'name': elderly_user['name']},
            'relationship': relationship
        }
    })


@app.get("/api/auth/my-elderly")
async def get_my_elderly(token: str):
    """获取家属绑定的所有老人"""
    payload = decode_token(token)
    if not payload:
        return JSONResponse({'status': 'error', 'message': '请先登录'}, status_code=401)

    user = get_user_by_id(payload['user_id'])
    if not user or user['role'] != 'family':
        return JSONResponse({'status': 'error', 'message': '只有家属可以查看'}, status_code=403)

    elderly_list = get_elderly_by_family(user['id'])

    return JSONResponse({
        'status': 'success',
        'data': elderly_list
    })


@app.get("/api/auth/my-family")
async def get_my_family(token: str):
    """获取老人绑定的所有家属"""
    payload = decode_token(token)
    if not payload:
        return JSONResponse({'status': 'error', 'message': '请先登录'}, status_code=401)

    user = get_user_by_id(payload['user_id'])
    if not user or user['role'] != 'elderly':
        return JSONResponse({'status': 'error', 'message': '只有老人可以查看'}, status_code=403)

    family_list = get_family_by_elderly(user['id'])

    return JSONResponse({
        'status': 'success',
        'data': family_list
    })


# ============================================================
# 事件上报 API
# ============================================================

@app.post("/api/report")
async def report_event(data: Dict[str, Any]):
    try:
        alert_type = data.get('type', '未知事件')
        level = data.get('level', '低')
        confidence = data.get('confidence', 0.0)
        source = data.get('source', 'unknown')
        elderly_phone = data.get('elderly_phone', '')
        timestamp = data.get('timestamp', get_beijing_time())

        elderly_id = None
        if elderly_phone:
            user = get_user_by_phone(elderly_phone)
            if user and user['role'] == 'elderly':
                elderly_id = user['id']

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (alert_type, level, confidence, source, elderly_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_type, level, confidence, source, elderly_id, timestamp))
            event_id = cursor.lastrowid
            conn.commit()

        message = {
            'type': 'new_alert',
            'data': {
                'id': event_id,
                'alert_type': alert_type,
                'level': level,
                'confidence': confidence,
                'source': source,
                'elderly_id': elderly_id,
                'timestamp': timestamp
            }
        }

        await manager.broadcast(message, room="family")

        return JSONResponse({
            'status': 'success',
            'message': '事件已接收并推送',
            'event_id': event_id,
            'timestamp': timestamp
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 其他 API（查询、反馈等保持不变）
# ============================================================

@app.get("/api/events/today")
async def get_today_events():
    today = get_beijing_now().strftime('%Y-%m-%d')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM events WHERE DATE(timestamp) = DATE(?)
            ORDER BY timestamp DESC
        ''', (today,))
        rows = cursor.fetchall()
        return JSONResponse({
            'status': 'success',
            'total': len(rows),
            'events': [dict(row) for row in rows]
        })


@app.get("/api/events/last_days/{days}")
async def get_events_last_days(days: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM events 
            WHERE timestamp >= DATE('now', ?)
            ORDER BY timestamp DESC
        ''', (f'-{days} days',))
        rows = cursor.fetchall()
        return JSONResponse({
            'status': 'success',
            'total': len(rows),
            'events': [dict(row) for row in rows]
        })


@app.get("/api/events/all")
async def get_all_events():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM events 
            WHERE timestamp >= DATE('now', '-15 days')
            ORDER BY timestamp DESC
        ''')
        rows = cursor.fetchall()
        return JSONResponse({
            'status': 'success',
            'total': len(rows),
            'events': [dict(row) for row in rows]
        })


@app.get("/api/events/trend")
async def get_trend_data():
    from datetime import timedelta
    import random
    from collections import Counter

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM events 
            WHERE timestamp >= DATE('now', '-7 days')
            ORDER BY timestamp ASC
        ''')
        rows = cursor.fetchall()
        events = [dict(row) for row in rows]

        day_count = {}
        for e in events:
            timestamp = e.get('timestamp', '')
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        if 'T' in timestamp:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                        date_key = dt.strftime('%m-%d')
                        day_count[date_key] = day_count.get(date_key, 0) + 1
                except:
                    continue

        beijing_now = get_beijing_now()
        trend_data = []
        for i in range(6, -1, -1):
            date = beijing_now - timedelta(days=i)
            date_key = date.strftime('%m-%d')
            count = day_count.get(date_key, 0)
            score = min(100, count * 8 + random.randint(-5, 15))
            score = max(0, score)
            trend_data.append({
                'date': date_key,
                'score': score,
                'count': count
            })

        return JSONResponse({
            'status': 'success',
            'trend_data': trend_data
        })


@app.get("/api/events/health")
async def get_health_data():
    from datetime import timedelta
    import random

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM events 
            WHERE timestamp >= DATE('now', '-7 days')
            ORDER BY timestamp ASC
        ''')
        rows = cursor.fetchall()
        events = [dict(row) for row in rows]

        day_count = {}
        for e in events:
            timestamp = e.get('timestamp', '')
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        if 'T' in timestamp:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                        date_key = dt.strftime('%m-%d')
                        day_count[date_key] = day_count.get(date_key, 0) + 1
                except:
                    continue

        beijing_now = get_beijing_now()
        health_data = []
        for i in range(6, -1, -1):
            date = beijing_now - timedelta(days=i)
            date_key = date.strftime('%m-%d')
            count = day_count.get(date_key, 0)
            index = max(0, min(100, 100 - count * 5 + random.randint(-10, 15)))
            health_data.append({
                'date': date_key,
                'index': index,
                'count': count
            })

        return JSONResponse({
            'status': 'success',
            'health_data': health_data
        })


# ============================================================
# 反馈 API
# ============================================================

@app.get("/api/feedback/user/{username}")
async def get_user_feedback(username: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM feedback WHERE username = ? ORDER BY created_at DESC', (username,))
        rows = cursor.fetchall()
        cursor.execute('SELECT * FROM feedback ORDER BY created_at DESC')
        all_rows = cursor.fetchall()
        return JSONResponse({
            'status': 'success',
            'user_feedbacks': [dict(row) for row in rows],
            'all_feedbacks': [dict(row) for row in all_rows]
        })


@app.post("/api/feedback/save")
async def save_feedback(data: Dict[str, Any]):
    try:
        username = data.get('username', 'unknown')
        event_time = data.get('event_time', '')
        feedback_type = data.get('feedback_type', '其他')
        description = data.get('description', '')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (username, event_time, feedback_type, description, status)
                VALUES (?, ?, ?, ?, '待处理')
            ''', (username, event_time, feedback_type, description))
            conn.commit()
        return JSONResponse({'status': 'success', 'message': '反馈已提交'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/feedback/{feedback_id}")
async def update_feedback(feedback_id: int, data: Dict[str, Any]):
    try:
        status = data.get('status', '待处理')
        notes = data.get('notes', '')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE feedback SET status = ?, notes = ?, handled_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (status, notes, feedback_id))
            conn.commit()
        return JSONResponse({'status': 'success', 'message': '反馈已更新'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback/user/all")
async def get_all_feedback():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM feedback 
            ORDER BY CASE WHEN status = '待处理' THEN 0 WHEN status = '处理中' THEN 1 ELSE 2 END, created_at DESC
        ''')
        rows = cursor.fetchall()
        return JSONResponse({
            'status': 'success',
            'total': len(rows),
            'feedbacks': [dict(row) for row in rows]
        })


@app.post("/api/admin/handle_feedback")
async def handle_feedback(data: Dict[str, Any]):
    try:
        feedback_id = data.get('id')
        status = data.get('status', '已处理')
        notes = data.get('notes', '')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE feedback SET status = ?, notes = ?, handled_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (status, notes, feedback_id))
            conn.commit()
            if cursor.rowcount == 0:
                return JSONResponse({'status': 'error', 'message': '反馈不存在'}, status_code=404)
        await manager.broadcast({
            'type': 'feedback_update',
            'message': f'反馈 #{feedback_id} 已处理'
        }, room="feedback")
        return JSONResponse({'status': 'success', 'message': '反馈已处理'})
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': str(e)}, status_code=500)


# ============================================================
# WebSocket 端点
# ============================================================

@app.websocket("/ws/family")
async def websocket_family(websocket: WebSocket):
    await manager.connect(websocket, room="family")
    try:
        await websocket.send_json({
            'type': 'connected',
            'message': '已连接到银龄安居实时推送',
            'timestamp': get_beijing_time()
        })
        while True:
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_text('pong')
    except WebSocketDisconnect:
        manager.disconnect(websocket, room="family")


@app.websocket("/ws/feedback")
async def websocket_feedback(websocket: WebSocket):
    await manager.connect(websocket, room="feedback")
    try:
        await websocket.send_json({
            'type': 'connected',
            'message': '已连接到反馈推送'
        })
        while True:
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_text('pong')
    except WebSocketDisconnect:
        manager.disconnect(websocket, room="feedback")


# ============================================================
# 健康检查
# ============================================================

@app.get("/health")
async def health_check():
    return {
        'status': 'healthy',
        'timestamp': get_beijing_time(),
        'connections': len(manager.active_connections)
    }


# ============================================================
# 启动服务
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)