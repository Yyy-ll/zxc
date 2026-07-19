# utils/feedback_dao.py
from utils.database import execute_query, execute_update, execute_insert
from datetime import datetime


def save_feedback(username, event_time, feedback_type, description):
    """保存用户反馈"""
    sql = """
        INSERT INTO feedback (username, event_time, feedback_type, description, status, created_at)
        VALUES (%s, %s, %s, %s, '待处理', NOW())
    """
    return execute_insert(sql, (username, event_time, feedback_type, description))


def get_feedback_list(status=None, limit=50, offset=0):
    """获取反馈列表"""
    sql = "SELECT * FROM feedback"
    params = []

    if status:
        sql += " WHERE status = %s"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return execute_query(sql, params)


def get_feedback_by_id(feedback_id):
    """获取单个反馈详情"""
    sql = "SELECT * FROM feedback WHERE id = %s"
    result = execute_query(sql, (feedback_id,))
    return result[0] if result else None


def update_feedback_status(feedback_id, status, handled_by=None, notes=None):
    """更新反馈状态"""
    sql = """
        UPDATE feedback 
        SET status = %s, 
            handled_by = %s, 
            handled_at = NOW(),
            notes = %s
        WHERE id = %s
    """
    return execute_update(sql, (status, handled_by, notes, feedback_id))


def get_feedback_stats():
    """获取反馈统计信息"""
    sql = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = '待处理' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = '处理中' THEN 1 ELSE 0 END) as processing,
            SUM(CASE WHEN status = '已处理' THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN status = '已忽略' THEN 1 ELSE 0 END) as ignored,
            COUNT(DISTINCT username) as unique_users
        FROM feedback
    """
    result = execute_query(sql)
    return result[0] if result else {}


def search_feedback(keyword, limit=50):
    """搜索反馈"""
    sql = """
        SELECT * FROM feedback 
        WHERE description LIKE %s 
           OR username LIKE %s
           OR feedback_type LIKE %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    keyword_pattern = f"%{keyword}%"
    return execute_query(sql, (keyword_pattern, keyword_pattern, keyword_pattern, limit))