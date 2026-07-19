# utils/database.py
import sqlite3
from pathlib import Path
import streamlit as st

# 数据库文件路径（在 falling_detect 目录下）
DB_PATH = Path(__file__).parent.parent / "falling_detect.db"


def get_db_connection():
    """获取 SQLite 数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(sql, params=None):
    """执行查询并返回结果列表（每行是字典）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def execute_update(sql, params=None):
    """执行更新/插入/删除，返回影响行数"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor.rowcount


def execute_insert(sql, params=None):
    """执行插入，返回最后插入的 ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor.lastrowid


def init_database():
    """初始化数据库：创建所有表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

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
                handled_by TEXT,
                handled_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 告警事件表（用于 risk.py, history.py, health.py, trend.py）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT,
                level TEXT,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        print("✅ SQLite 数据库初始化完成")