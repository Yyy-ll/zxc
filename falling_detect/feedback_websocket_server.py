# feedback_websocket_server.py
import asyncio
import json
import threading
import time
import pymysql
from datetime import datetime
import websockets
from websockets.server import serve

# ============================================================
# WebSocket 服务器配置
# ============================================================
WS_HOST = '0.0.0.0'
WS_PORT = 8766

# 存储所有连接的客户端
connected_clients = set()

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Zxc123654',
    'database': 'silver_home',
    'charset': 'utf8mb4'
}


# ============================================================
# 工具函数
# ============================================================
def convert_datetime_to_str(obj):
    """递归转换对象中的 datetime 为字符串"""
    if isinstance(obj, dict):
        return {k: convert_datetime_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return obj


# ============================================================
# 数据库监听器
# ============================================================
class FeedbackDatabaseListener:
    """监听 feedback 表变化"""

    def __init__(self):
        self.last_records = {}
        self._running = False
        self._thread = None
        self.last_check_time = datetime.now()

    def start(self):
        """启动监听线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        print("✅ Feedback 数据库监听器已启动")

    def stop(self):
        """停止监听"""
        self._running = False

    def _listen(self):
        """监听数据库变化"""
        self._init_state()

        while self._running:
            try:
                self._check_feedback_changes()
                time.sleep(2)
            except Exception as e:
                print(f"监听 feedback 表出错: {e}")
                time.sleep(5)

    def _init_state(self):
        """初始化状态"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""
                SELECT id, status, updated_at 
                FROM feedback
            """)
            records = cursor.fetchall()

            for r in records:
                self.last_records[r['id']] = {
                    'status': r['status'],
                    'updated_at': r['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if r['updated_at'] else None
                }

            cursor.close()
            conn.close()
            print(f"📊 Feedback 初始化: {len(self.last_records)} 条记录")

        except Exception as e:
            print(f"初始化 feedback 状态失败: {e}")

    def _check_feedback_changes(self):
        """检查 feedback 表变化"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""
                SELECT id, username, feedback_type, description, status, created_at, updated_at
                FROM feedback
                ORDER BY id
            """)
            current_records = cursor.fetchall()

            for record in current_records:
                record_id = record['id']
                current_status = record['status']
                current_updated_at = record['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if record['updated_at'] else None

                if record_id not in self.last_records:
                    print(f"📝 新增反馈 #{record_id}: {record['feedback_type']} - {current_status}")

                    asyncio.run(self._broadcast({
                        'type': 'feedback_update',
                        'action': 'insert',
                        'data': convert_datetime_to_str(record),
                        'timestamp': datetime.now().isoformat()
                    }))

                    self.last_records[record_id] = {
                        'status': current_status,
                        'updated_at': current_updated_at
                    }
                else:
                    old_status = self.last_records[record_id]['status']

                    if old_status != current_status:
                        print(f"🔄 反馈 #{record_id} 状态变化: {old_status} -> {current_status}")

                        asyncio.run(self._broadcast({
                            'type': 'feedback_update',
                            'action': 'update',
                            'data': convert_datetime_to_str(record),
                            'old_status': old_status,
                            'new_status': current_status,
                            'timestamp': datetime.now().isoformat()
                        }))

                        self.last_records[record_id] = {
                            'status': current_status,
                            'updated_at': current_updated_at
                        }
                    else:
                        old_updated_at = self.last_records[record_id].get('updated_at')
                        if old_updated_at != current_updated_at and current_updated_at:
                            self.last_records[record_id]['updated_at'] = current_updated_at

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"检查 feedback 变化失败: {e}")
            import traceback
            traceback.print_exc()

    async def _broadcast(self, message):
        """广播消息给所有连接的客户端"""
        if not connected_clients:
            print(f"⚠️ 没有连接的客户端，消息未发送")
            return

        message = convert_datetime_to_str(message)
        msg_json = json.dumps(message, ensure_ascii=False)

        print(f"📤 广播消息: {message.get('action')} - 客户端数: {len(connected_clients)}")

        disconnected = set()
        sent_count = 0

        for client in connected_clients:
            try:
                await client.send(msg_json)
                sent_count += 1
            except Exception as e:
                print(f"❌ 发送消息失败: {e}")
                disconnected.add(client)

        print(f"✅ 消息已发送给 {sent_count} 个客户端")

        for client in disconnected:
            connected_clients.remove(client)


# ============================================================
# WebSocket 处理器
# ============================================================
async def handle_client(websocket, path):
    """处理 WebSocket 连接"""
    client_id = id(websocket)
    print(f"🔗 Feedback 客户端 {client_id} 已连接")
    print(f"📊 当前连接数: {len(connected_clients) + 1}")

    connected_clients.add(websocket)

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')

                if msg_type == 'subscribe':
                    channel = data.get('channel', 'feedback')
                    print(f"📡 客户端 {client_id} 订阅了: {channel}")

                    await websocket.send(json.dumps({
                        'type': 'subscribed',
                        'channel': channel,
                        'message': f'已订阅 {channel} 频道'
                    }))

                elif msg_type == 'ping':
                    await websocket.send(json.dumps({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }))

                else:
                    print(f"📩 收到未知类型消息: {msg_type}")

            except json.JSONDecodeError:
                print(f"❌ 无效的JSON消息: {message}")
            except Exception as e:
                print(f"❌ 处理消息出错: {e}")

    except websockets.exceptions.ConnectionClosed:
        print(f"🔌 Feedback 客户端 {client_id} 断开连接")
    finally:
        connected_clients.remove(websocket)
        print(f"📊 当前连接数: {len(connected_clients)}")


# ============================================================
# 启动服务器
# ============================================================
async def main():
    """启动 WebSocket 服务器"""
    print("🚀 Feedback WebSocket 服务器启动")
    print(f"📍 地址: ws://{WS_HOST}:{WS_PORT}")
    print("📊 监听: feedback 表变化")
    print("=" * 50)

    listener = FeedbackDatabaseListener()
    listener.start()

    async with serve(handle_client, WS_HOST, WS_PORT):
        print("✅ WebSocket 服务已启动，等待连接...")
        await asyncio.Future()


def run_websocket_server():
    """运行 WebSocket 服务器"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Feedback WebSocket 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器错误: {e}")


if __name__ == "__main__":
    run_websocket_server()