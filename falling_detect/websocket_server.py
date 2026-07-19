# websocket_server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json
import asyncio
import random
from datetime import datetime, timedelta
import uvicorn
import pymysql

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 数据库配置
# ============================================================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Zxc123654',  # 修改为你的密码
    'database': 'silver_home',
    'charset': 'utf8mb4'
}


# ============================================================
# Pydantic 模型
# ============================================================
class AlertData(BaseModel):
    id: str = None
    event_id: str = None
    alert_type: str
    level: str = "低"
    device_id: str = ""
    device_name: str = ""
    location: str = ""
    message: str = ""
    status: str = "待处理"
    timestamp: str = None


class EventsResponse(BaseModel):
    status: str
    total: int
    events: list


# ============================================================
# 数据库操作
# ============================================================
def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def save_alert_to_db(alert_data):
    """保存告警到数据库"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        event_id = alert_data.get('id') or alert_data.get('event_id') or str(int(datetime.now().timestamp() * 1000))

        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM risk_events WHERE event_id = %s",
            (str(event_id),)
        )
        if cursor.fetchone():
            return False

        sql = """
            INSERT INTO risk_events 
            (event_id, alert_type, level, device_id, device_name, location, message, status, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            str(event_id),
            alert_data.get('alert_type', '未知事件'),
            alert_data.get('level', '低'),
            alert_data.get('device_id', ''),
            alert_data.get('device_name', ''),
            alert_data.get('location', ''),
            alert_data.get('message', ''),
            alert_data.get('status', '待处理'),
            alert_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ))

        conn.commit()
        return True

    except Exception as e:
        print(f"保存告警失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_today_events():
    """获取今天的所有事件"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = """
            SELECT * FROM risk_events 
            WHERE DATE(timestamp) = CURDATE()
            ORDER BY timestamp DESC
        """
        cursor.execute(sql)
        return cursor.fetchall()

    except Exception as e:
        print(f"获取事件失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_events_by_days(days=7):
    """获取最近N天的事件"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = """
            SELECT * FROM risk_events 
            WHERE timestamp > DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY timestamp DESC
        """
        cursor.execute(sql, (days,))
        return cursor.fetchall()

    except Exception as e:
        print(f"获取事件失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# HTTP API
# ============================================================
@app.post("/api/save_alert")
async def save_alert(alert: AlertData):
    """保存告警到数据库"""
    try:
        alert_dict = alert.dict(exclude_none=True)
        # 确保有 event_id
        if not alert_dict.get('event_id') and not alert_dict.get('id'):
            alert_dict['event_id'] = str(int(datetime.now().timestamp() * 1000))

        # 转换 id 为 event_id（兼容）
        if alert_dict.get('id') and not alert_dict.get('event_id'):
            alert_dict['event_id'] = alert_dict['id']

        success = save_alert_to_db(alert_dict)
        if success:
            return {"status": "success", "message": "事件已保存"}
        else:
            return {"status": "exists", "message": "事件已存在"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save_alerts")
async def save_alerts(alerts: list):
    """批量保存告警"""
    try:
        success_count = 0
        for alert in alerts:
            if save_alert_to_db(alert):
                success_count += 1
        return {"status": "success", "saved": success_count, "total": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_today_events")
async def get_today():
    """获取今天的所有事件"""
    try:
        events = get_today_events()
        return {"status": "success", "total": len(events), "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_events")
async def get_events(days: int = 7):
    """获取最近N天的事件"""
    try:
        events = get_events_by_days(days)
        return {"status": "success", "total": len(events), "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# WebSocket 端点
# ============================================================
connected_clients = set()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"✅ 客户端已连接，当前连接数: {len(connected_clients)}")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print(f"❌ 客户端断开，当前连接数: {len(connected_clients)}")


async def broadcast_message(message: dict):
    """向所有客户端广播消息"""
    if not connected_clients:
        return

    message_str = json.dumps(message, ensure_ascii=False)
    disconnected = []

    for client in connected_clients:
        try:
            await client.send_text(message_str)
        except:
            disconnected.append(client)

    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)


# ============================================================
# 模拟数据生成器
# ============================================================
DEVICES = [
    {"id": "DEV1001", "name": "客厅摄像头", "location": "客厅"},
    {"id": "DEV1002", "name": "卧室摄像头", "location": "卧室"},
    {"id": "DEV1003", "name": "走廊摄像头", "location": "走廊"},
    {"id": "DEV1004", "name": "卫生间传感器", "location": "卫生间"},
]

ALERT_TYPES = ["跌倒告警", "人形检测", "移动侦测", "步态异常", "长时间静坐", "夜间离床"]
LEVELS = ["低", "中", "高"]


def generate_alert():
    """生成模拟告警数据"""
    device = random.choice(DEVICES)
    alert_type = random.choice(ALERT_TYPES)
    level = random.choices(LEVELS, weights=[0.3, 0.4, 0.3])[0]

    return {
        "type": "alert",
        "id": f"EVT{random.randint(100000, 999999)}",
        "alert_type": alert_type,
        "device_id": device["id"],
        "device_name": device["name"],
        "location": device["location"],
        "level": level,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": f"检测到{alert_type}事件",
        "status": random.choice(["待处理", "处理中", "已处理", "误报"])
    }


async def push_alerts():
    """每3-8秒推送告警（同时保存到数据库）"""
    count = 0
    while True:
        await asyncio.sleep(random.randint(3, 8))
        count += 1
        alert = generate_alert()
        print(f"📢 推送告警 #{count}: {alert['alert_type']} - {alert['location']}")

        # 保存到数据库
        save_alert_to_db(alert)

        # 广播给所有客户端
        await broadcast_message(alert)


async def push_device_status():
    """每10-20秒推送设备状态"""
    count = 0
    while True:
        await asyncio.sleep(random.randint(10, 20))
        count += 1
        device = random.choice(DEVICES)
        status = random.choices(["online", "offline", "warning"], weights=[0.8, 0.1, 0.1])[0]
        status_map = {"online": "🟢 在线", "offline": "🔴 离线", "warning": "🟡 异常"}

        status_data = {
            "type": "device_status",
            "device_id": device["id"],
            "device_name": device["name"],
            "status": status,
            "status_text": status_map[status],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        print(f"📡 推送设备状态 #{count}: {device['name']} -> {status_map[status]}")
        await broadcast_message(status_data)


async def push_health_data():
    """每15-25秒推送心理健康数据"""
    while True:
        await asyncio.sleep(random.randint(15, 25))
        index = random.randint(30, 85)
        status = random.choices(["正常", "轻度关注", "需要关注"], weights=[0.5, 0.35, 0.15])[0]

        data = {
            "type": "health_data",
            "index": index,
            "change": random.randint(-20, 30),
            "status": status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "suggestion": random.choice([
                "连续3天活动量下降超过20%，建议家属增加陪伴时间。",
                "近一周社交互动减少，建议安排亲友探访或视频通话。",
                "睡眠质量有所下降，建议调整作息时间。",
                "情绪状态稳定，继续保持良好的生活习惯。",
                "活动量适中，建议保持当前节奏。"
            ])
        }
        print(f"❤️ 推送心理健康数据: 指数 {index} - {status}")
        await broadcast_message(data)


async def push_trend_data():
    """每20-30秒推送趋势数据"""
    while True:
        await asyncio.sleep(random.randint(20, 30))
        factors = ["步态不稳", "活动减少", "睡眠质量下降", "心率异常", "环境安全风险"]

        data = {
            "type": "trend_data",
            "risk_score": random.randint(20, 75),
            "trend": random.choices(["上升", "下降", "稳定"], weights=[0.3, 0.3, 0.4])[0],
            "main_factor": random.choice(factors),
            "accuracy": random.randint(85, 98),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "suggestion": random.choice([
                "近期步态稳定性有所下降，建议减少独自行走时间。",
                "活动量持续减少，建议制定每日活动计划。",
                "睡眠质量下降，建议保持规律作息。",
                "心率波动较大，建议定期监测。"
            ])
        }
        print(f"📈 推送趋势数据: 风险 {data['risk_score']} - {data['trend']}")
        await broadcast_message(data)


# ============================================================
# 启动服务
# ============================================================
@app.on_event("startup")
async def startup_event():
    print("🚀 WebSocket 服务器已启动")
    try:
        from utils.db import clear_today_events, get_today_events
        # 检查今天是否有数据，如果有说明是当天，不清理
        events = get_today_events()
        if len(events) == 0:
            # 检查昨天是否有数据需要清理
            print("📊 今天暂无数据，检查是否需要清理旧数据...")
    except Exception as e:
        print(f"⚠️ 清理检查失败: {e}")
    print("=" * 50)
    print("📡 正在模拟数据推送:")
    print("  - 告警数据 (每3-8秒，同时保存到数据库)")
    print("  - 设备状态 (每10-20秒)")
    print("  - 心理健康数据 (每15-25秒)")
    print("  - 趋势数据 (每20-30秒)")
    print("=" * 50)
    print("📊 HTTP API 接口:")
    print("  - POST /api/save_alert   保存单条告警")
    print("  - POST /api/save_alerts  批量保存告警")
    print("  - GET  /api/get_today_events  获取今日事件")
    print("  - GET  /api/get_events  获取历史事件")
    print("=" * 50)

    asyncio.create_task(push_alerts())
    asyncio.create_task(push_device_status())
    asyncio.create_task(push_health_data())
    asyncio.create_task(push_trend_data())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)