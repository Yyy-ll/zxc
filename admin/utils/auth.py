# admin/utils/auth.py
import streamlit as st
import yaml
import os
import hashlib
from functools import wraps
from datetime import datetime


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    if not os.path.exists(config_path):
        # 如果配置文件不存在，使用默认配置
        return {
            'credentials': {
                'usernames': {
                    'admin': {
                        'password': 'admin123',
                        'name': '管理员'
                    }
                }
            },
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


def check_password(username, password):
    """验证用户名和密码"""
    config = load_config()
    credentials = config.get('credentials', {}).get('usernames', {})

    if username in credentials:
        stored_password = credentials[username].get('password', '')
        # 直接比较明文密码（因为 config.yaml 中存的是明文）
        return stored_password == password
    return False


def login(username, password):
    """登录验证"""
    if check_password(username, password):
        st.session_state.authenticated = True
        st.session_state.username = username
        config = load_config()
        credentials = config.get('credentials', {}).get('usernames', {})
        # 获取用户显示名称
        user_data = credentials.get(username, {})
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        if first_name or last_name:
            st.session_state.name = f"{first_name}{last_name}".strip()
        else:
            st.session_state.name = username
        st.session_state.login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return True
    return False


def logout():
    """登出"""
    keys = ['authenticated', 'username', 'name', 'login_time']
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.logout_clicked = True


def require_auth(func):
    """登录验证装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            st.error("🔒 请先登录")
            st.info("请在侧边栏输入用户名和密码登录")
            st.stop()
            return None
        return func(*args, **kwargs)
    return wrapper


def is_admin():
    """检查是否为管理员"""
    return st.session_state.get('username') == 'admin'


def get_current_user():
    """获取当前用户信息"""
    return {
        'username': st.session_state.get('username', ''),
        'name': st.session_state.get('name', ''),
        'login_time': st.session_state.get('login_time', '')
    }