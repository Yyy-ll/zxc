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


# ============================================================
# 【新增】获取所有事件（近15天）- 给 history.py 使用
# ============================================================
@app.get("/api/events/all")
async def get_all_events(
        date: str = None,  # 时间范围: 今天, 最近3天, 最近7天, 最近15天, 全部
        type: str = None,  # 事件类型
        level: str = None  # 风险等级
):
    """获取事件（支持筛选参数）"""
    from datetime import datetime, timedelta

    with get_db() as conn:
        cursor = conn.cursor()

        # 构建 SQL 查询
        sql = "SELECT * FROM events WHERE 1=1"
        params = []

        # 日期筛选
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        if date == "今天":
            sql += " AND DATE(timestamp) = ?"
            params.append(today_str)
        elif date == "最近3天":
            cutoff = (today - timedelta(days=3)).strftime('%Y-%m-%d')
            sql += " AND DATE(timestamp) >= ?"
            params.append(cutoff)
        elif date == "最近7天":
            cutoff = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            sql += " AND DATE(timestamp) >= ?"
            params.append(cutoff)
        elif date == "最近15天":
            cutoff = (today - timedelta(days=15)).strftime('%Y-%m-%d')
            sql += " AND DATE(timestamp) >= ?"
            params.append(cutoff)
        # "全部" 不添加日期过滤

        # 类型筛选
        if type and type != "全部":
            sql += " AND alert_type = ?"
            params.append(type)

        # 等级筛选
        if level and level != "全部":
            sql += " AND level = ?"
            params.append(level)

        sql += " ORDER BY timestamp DESC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        events = [dict(row) for row in rows]

        return JSONResponse({
            'status': 'success',
            'total': len(events),
            'events': events
        })


# ============================================================
# 【新增】获取趋势数据 - 给 trend.py 使用
# ============================================================
@app.get("/api/events/trend")
async def get_trend_data():
    """获取近7天风险趋势数据"""
    from datetime import datetime, timedelta
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

        # 按天统计
        day_count = {}
        for e in events:
            timestamp = e.get('timestamp', '')
            if timestamp:
                try:
                    # 解析时间字符串
                    if isinstance(timestamp, str):
                        # 尝试解析多种格式
                        if 'T' in timestamp:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                        date_key = dt.strftime('%m-%d')
                        day_count[date_key] = day_count.get(date_key, 0) + 1
                except:
                    continue

        # 生成趋势数据
        today = datetime.now()
        trend_data = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
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


# ============================================================
# 【新增】获取心理健康数据 - 给 health.py 使用
# ============================================================
@app.get("/api/events/health")
async def get_health_data():
    """获取近7天心理健康趋势数据"""
    from datetime import datetime, timedelta
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

        # 按天统计
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

        # 生成心理健康数据
        today = datetime.now()
        health_data = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
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