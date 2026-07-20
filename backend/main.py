# backend/main.py - FastAPI 后端服务
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
import os
from contextlib import contextmanager
import uvicorn

app = FastAPI(title="银龄安居 - 跌倒检测后端")

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
        # 事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT,
                level TEXT,
                confidence REAL,
                source TEXT,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 反馈表
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
        conn.commit()
        print("✅ 数据库初始化完成")


# 初始化数据库
init_db()


# ============================================================
# WebSocket 连接管理
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
# API 接口
# ============================================================

@app.post("/api/report")
async def report_event(data: Dict[str, Any]):
    """接收 Jetson 上报的跌倒事件"""
    try:
        alert_type = data.get('type', '未知事件')
        level = data.get('level', '低')
        confidence = data.get('confidence', 0.0)
        source = data.get('source', 'unknown')
        timestamp = data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # 保存到数据库
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (alert_type, level, confidence, source, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (alert_type, level, confidence, source, timestamp))
            event_id = cursor.lastrowid
            conn.commit()

        # 构造推送消息
        message = {
            'type': 'new_alert',
            'data': {
                'id': event_id,
                'alert_type': alert_type,
                'level': level,
                'confidence': confidence,
                'source': source,
                'timestamp': timestamp
            }
        }

        # WebSocket 广播给所有家属端
        await manager.broadcast(message, room="family")

        return JSONResponse({
            'status': 'success',
            'message': '事件已接收并推送',
            'event_id': event_id
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events/today")
async def get_today_events():
    """获取今天的所有事件"""
    today = datetime.now().strftime('%Y-%m-%d')
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
    """获取最近 N 天的事件"""
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


@app.get("/api/feedback/user/{username}")
async def get_user_feedback(username: str):
    """获取用户的反馈"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM feedback WHERE username = ?
            ORDER BY created_at DESC
        ''', (username,))
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
    """保存用户反馈"""
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

        return JSONResponse({
            'status': 'success',
            'message': '反馈已提交'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/feedback/{feedback_id}")
async def update_feedback(feedback_id: int, data: Dict[str, Any]):
    """更新反馈状态（管理员用）"""
    try:
        status = data.get('status', '待处理')
        notes = data.get('notes', '')

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE feedback 
                SET status = ?, notes = ?, handled_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, notes, feedback_id))
            conn.commit()

        return JSONResponse({
            'status': 'success',
            'message': '反馈已更新'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# WebSocket 端点
# ============================================================

@app.websocket("/ws/family")
async def websocket_family(websocket: WebSocket):
    """家属端 WebSocket 连接"""
    await manager.connect(websocket, room="family")
    try:
        # 发送连接成功消息
        await websocket.send_json({
            'type': 'connected',
            'message': '已连接到银龄安居实时推送',
            'timestamp': datetime.now().isoformat()
        })

        # 保持连接，接收心跳
        while True:
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_text('pong')

    except WebSocketDisconnect:
        manager.disconnect(websocket, room="family")
        print("❌ 家属端 WebSocket 断开")


@app.websocket("/ws/feedback")
async def websocket_feedback(websocket: WebSocket):
    """反馈 WebSocket 连接"""
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
        'timestamp': datetime.now().isoformat(),
        'connections': len(manager.active_connections)
    }


# ============================================================
# 启动服务
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)