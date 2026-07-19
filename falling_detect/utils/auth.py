# utils/auth.py
import streamlit as st
from functools import wraps
from typing import Callable


# ========== 登录验证装饰器 ==========
def require_auth(func: Callable) -> Callable:
    """
    页面登录验证装饰器
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 检查登录状态
        auth_status = st.session_state.get('authentication_status', False)

        # 如果未登录，显示提示并停止渲染
        if not auth_status:
            st.error("🔒 请先登录系统")
            st.info("请在左侧侧边栏输入账号和密码登录")
            st.stop()
            return None

        # 检查用户名是否存在（额外的安全验证）
        if 'username' not in st.session_state:
            st.error("⚠️ 会话已过期，请重新登录")
            st.stop()
            return None

        # 登录有效，执行原函数
        return func(*args, **kwargs)

    return wrapper


# ========== 登录状态检查函数 ==========
def check_login_status() -> bool:
    """检查当前登录状态"""
    return st.session_state.get('authentication_status', False)


# ========== 获取当前用户信息 ==========
def get_current_user() -> dict:
    """获取当前登录用户信息"""
    return {
        'name': st.session_state.get('name', '未知用户'),
        'username': st.session_state.get('username', '')
    }


# ========== 登出函数 ==========
def logout() -> None:
    """用户登出，清除所有会话状态"""
    keys_to_remove = ['authentication_status', 'name', 'username', 'logout']
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

    # 设置登出标志
    st.session_state.logout_clicked = True