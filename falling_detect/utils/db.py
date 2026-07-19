# utils/db.py
from utils.database import execute_query
from datetime import datetime, timedelta


def get_today_events():
    """获取今天的所有事件"""
    today = datetime.now().strftime('%Y-%m-%d')
    sql = """
        SELECT * FROM events 
        WHERE DATE(timestamp) = DATE(?)
        ORDER BY timestamp DESC
    """
    return execute_query(sql, (today,))


def get_events_last_days(days=7):
    """获取最近 N 天的事件"""
    sql = """
        SELECT * FROM events 
        WHERE timestamp >= DATE('now', ?)
        ORDER BY timestamp DESC
    """
    return execute_query(sql, (f'-{days} days',))


def get_all_events():
    """获取所有事件"""
    sql = "SELECT * FROM events ORDER BY timestamp DESC"
    return execute_query(sql)


def get_event_stats():
    """获取事件统计"""
    sql = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN level = '高' THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN level = '中' THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN level = '低' THEN 1 ELSE 0 END) as low
        FROM events
        WHERE DATE(timestamp) = DATE('now')
    """
    result = execute_query(sql)
    return result[0] if result else {'total': 0, 'high': 0, 'medium': 0, 'low': 0}