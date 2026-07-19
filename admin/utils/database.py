# admin/utils/database.py
import pymysql
import streamlit as st
from contextlib import contextmanager
import yaml
import os

def get_db_config():
    """从配置文件读取数据库配置"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('database', {})

@contextmanager
def get_db_connection():
    """获取数据库连接"""
    db_config = get_db_config()
    conn = None
    try:
        conn = pymysql.connect(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 3306),
            user=db_config.get('user', 'root'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'silver_home'),
            charset='utf8mb4'
        )
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