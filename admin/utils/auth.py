# admin/utils/auth.py
import streamlit as st
import yaml
import os
from functools import wraps


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_password(username, password):
    """验证用户名和密码"""
    config = load_config()
    credentials = config.get('credentials', {}).get('usernames', {})

    if username in credentials:
        # 这里使用简单验证，生产环境建议使用加密
        # 由于密码是加密存储的，这里简化处理
        return credentials[username].get('password') == password
    return False


def login(username, password):
    """登录验证"""
    if check_password(username, password):
        st.session_state.authenticated = True
        st.session_state.username = username
        config = load_config()
        credentials = config.get('credentials', {}).get('usernames', {})
        st.session_state.name = credentials.get(username, {}).get('name', username)
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