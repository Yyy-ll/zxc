# admin/utils/database.py
import pymysql
import streamlit as st
from contextlib import contextmanager
import yaml
import os


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    if not os.path.exists(config_path):
        # 如果配置文件不存在，返回默认配置
        return {
            'database': {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': 'silver_home'
            }
        }
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_db_config():
    """从配置文件读取数据库配置"""
    config = load_config()
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
            charset='utf8mb4',
            connect_timeout=10
        )
        yield conn
    except pymysql.err.OperationalError as e:
        st.error(f"❌ 数据库连接失败: {e}")
        st.info("💡 请检查数据库配置是否正确，或使用 API 方式获取数据")
        raise
    except Exception as e:
        st.error(f"❌ 数据库错误: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(sql, params=None):
    """执行查询并返回结果"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
    except Exception as e:
        st.error(f"❌ 查询失败: {e}")
        return []


def execute_update(sql, params=None):
    """执行更新操作"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount
    except Exception as e:
        st.error(f"❌ 更新失败: {e}")
        return 0


def execute_insert(sql, params=None):
    """执行插入操作并返回插入ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.lastrowid
    except Exception as e:
        st.error(f"❌ 插入失败: {e}")
        return None