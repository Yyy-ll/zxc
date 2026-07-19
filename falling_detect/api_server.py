# api_server.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymysql
from datetime import datetime
from decimal import Decimal
import uvicorn

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
    'port': 3306,
    'user': 'root',
    'password': 'Zxc123654',
    'database': 'silver_home',
    'charset': 'utf8mb4'
}


# ============================================================
# 辅助函数
# ============================================================
def convert_to_serializable(obj):
    """递归转换对象为 JSON 可序列化的格式"""
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [convert_to_serializable(item) for item in obj]
    else:
        return obj


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def execute_query(sql, params=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def execute_update(sql, params=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def save_feedback(username, event_time, feedback_type, description):
    sql = """
        INSERT INTO feedback (username, event_time, feedback_type, description, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, '待处理', NOW(), NOW())
    """
    return execute_update(sql, (username, event_time, feedback_type, description))


# ============================================================
# Pydantic 模型
# ============================================================
class FeedbackSave(BaseModel):
    username: str
    event_time: str
    feedback_type: str
    description: str


class FeedbackHandle(BaseModel):
    id: int
    status: str
    notes: str
    handled_by: str = "管理员"


# ============================================================
# API 接口
# ============================================================
@app.get("/api/admin/data")
async def get_admin_data():
    """获取管理面板数据"""
    stats_sql = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = '待处理' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = '处理中' THEN 1 ELSE 0 END) as processing,
            SUM(CASE WHEN status = '已处理' THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN status = '已忽略' THEN 1 ELSE 0 END) as ignored,
            COUNT(DISTINCT username) as unique_users
        FROM feedback
    """
    stats = execute_query(stats_sql)
    stats = stats[0] if stats else {}

    sql = """
        SELECT * FROM feedback 
        ORDER BY CASE WHEN status = '待处理' THEN 0 WHEN status = '处理中' THEN 1 ELSE 2 END, created_at DESC
    """
    feedbacks = execute_query(sql)

    stats = convert_to_serializable(stats)
    feedbacks = convert_to_serializable(feedbacks)

    return {
        "status": "success",
        "stats": stats,
        "feedbacks": feedbacks,
        "total": len(feedbacks) if feedbacks else 0
    }


@app.post("/api/admin/handle_feedback")
async def handle_feedback(data: FeedbackHandle):
    """处理反馈"""
    sql = """
        UPDATE feedback 
        SET status = %s, handled_by = %s, handled_at = NOW(), notes = %s
        WHERE id = %s
    """
    execute_update(sql, (data.status, data.handled_by, data.notes, data.id))
    return {"status": "success", "message": "反馈已处理"}


@app.get("/api/feedback/user/{username}")
async def get_user_feedback(username: str):
    """获取用户反馈"""
    sql = "SELECT * FROM feedback WHERE username = %s ORDER BY created_at DESC"
    user_feedbacks = execute_query(sql, (username,))
    all_sql = "SELECT * FROM feedback ORDER BY created_at DESC"
    all_feedbacks = execute_query(all_sql)

    user_feedbacks = convert_to_serializable(user_feedbacks)
    all_feedbacks = convert_to_serializable(all_feedbacks)

    return {
        "status": "success",
        "all_feedbacks": all_feedbacks,
        "user_feedbacks": user_feedbacks
    }


@app.post("/api/feedback/save")
async def save_feedback_api(data: FeedbackSave):
    """保存反馈"""
    save_feedback(data.username, data.event_time, data.feedback_type, data.description)
    return {"status": "success", "message": "反馈已提交"}


if __name__ == "__main__":
    # 端口改为 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)