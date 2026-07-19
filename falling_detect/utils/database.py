# utils/database.py
import pymysql
import streamlit as st
from contextlib import contextmanager
import os

# ===== 使用您的密码 =====
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Zxc123654',  # ← 改成您的密码
    'database': 'silver_home',
    'charset': 'utf8mb4'
}

@contextmanager
def get_db_connection():
    """获取数据库连接（使用上下文管理器）"""
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        yield conn
    except Exception as e:
        st.error(f"❌ 数据库连接失败: {e}")
        raise
    finally:
        if conn:
            conn.close()

def execute_query(sql, params=None):
    """执行查询并返回结果"""
    with get_db_connection() as conn:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

def execute_update(sql, params=None):
    """执行更新操作"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount

def execute_insert(sql, params=None):
    """执行插入操作并返回插入ID"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
            return cursor.lastrowid