# utils/db.py
import pymysql
import json
from datetime import datetime
import streamlit as st

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Zxc123654',
    'database': 'silver_home',
    'charset': 'utf8mb4'
}


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def save_alert_to_db(alert_data):
    """保存告警到数据库"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        event_id = alert_data.get('id') or alert_data.get('event_id')
        if not event_id:
            event_id = str(int(datetime.now().timestamp() * 1000))

        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM risk_events WHERE event_id = %s",
            (str(event_id),)
        )
        if cursor.fetchone():
            return False

        # 处理 timestamp
        timestamp = alert_data.get('timestamp')
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')

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
            timestamp
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


def save_device_status_to_db(status_data):
    """保存设备状态到数据库"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        timestamp = status_data.get('timestamp')
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')

        sql = """
            INSERT INTO device_status 
            (device_id, device_name, status, status_text, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            device_name = VALUES(device_name),
            status = VALUES(status),
            status_text = VALUES(status_text),
            timestamp = VALUES(timestamp)
        """
        cursor.execute(sql, (
            status_data.get('device_id', ''),
            status_data.get('device_name', ''),
            status_data.get('status', ''),
            status_data.get('status_text', ''),
            timestamp
        ))

        conn.commit()
        return True

    except Exception as e:
        print(f"保存设备状态失败: {e}")
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


def get_events_by_date(date_str):
    """获取指定日期的事件"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = """
            SELECT * FROM risk_events 
            WHERE DATE(timestamp) = %s
            ORDER BY timestamp DESC
        """
        cursor.execute(sql, (date_str,))
        return cursor.fetchall()

    except Exception as e:
        print(f"获取事件失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_events_last_days(days=7):
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


def get_all_events(limit=1000):
    """获取所有事件（限制数量）"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = """
            SELECT * FROM risk_events 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        cursor.execute(sql, (limit,))
        return cursor.fetchall()

    except Exception as e:
        print(f"获取所有事件失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def clear_old_events(days=7):
    """清除N天前的事件"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "DELETE FROM risk_events WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)"
        cursor.execute(sql, (days,))
        deleted = cursor.rowcount

        sql2 = "DELETE FROM device_status WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)"
        cursor.execute(sql2, (days,))

        conn.commit()
        return deleted

    except Exception as e:
        print(f"清除旧事件失败: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def clear_today_events():
    """清除今天的所有事件（用于每日重置）"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "DELETE FROM risk_events WHERE DATE(timestamp) = CURDATE()"
        cursor.execute(sql)
        deleted = cursor.rowcount
        conn.commit()

        if deleted > 0:
            print(f"🗑️ 已清除今天的所有事件: {deleted} 条")
        return deleted

    except Exception as e:
        print(f"清除今日事件失败: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_event_stats():
    """获取事件统计信息"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("SELECT COUNT(*) as total FROM risk_events WHERE DATE(timestamp) = CURDATE()")
        today = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) as total FROM risk_events WHERE timestamp > DATE_SUB(NOW(), INTERVAL 7 DAY)")
        week = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) as total FROM risk_events WHERE timestamp > DATE_SUB(NOW(), INTERVAL 30 DAY)")
        month = cursor.fetchone()

        cursor.execute("""
            SELECT alert_type, COUNT(*) as count 
            FROM risk_events 
            WHERE DATE(timestamp) = CURDATE() 
            GROUP BY alert_type
        """)
        by_type = cursor.fetchall()

        return {
            'today': today['total'] if today else 0,
            'week': week['total'] if week else 0,
            'month': month['total'] if month else 0,
            'by_type': by_type
        }

    except Exception as e:
        print(f"获取统计信息失败: {e}")
        return {'today': 0, 'week': 0, 'month': 0, 'by_type': []}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()