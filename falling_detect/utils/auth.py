# utils/auth.py
import streamlit as st
import requests
from functools import wraps
from typing import Callable, Optional, Dict

API_BASE = "https://zxc-production-f99b.up.railway.app"


def login_user(phone: str, password: str) -> tuple:
    """调用后端登录 API"""
    try:
        response = requests.post(
            f"{API_BASE}/api/auth/login",
            json={"phone": phone, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                user_data = data['data']
                st.session_state['token'] = user_data['token']
                st.session_state['user'] = user_data['user']
                st.session_state['bindings'] = user_data.get('bindings', [])
                st.session_state['authenticated'] = True
                return True, "登录成功"
            return False, data.get('message', '登录失败')
        elif response.status_code == 404:
            return False, "账号不存在"
        elif response.status_code == 401:
            return False, "密码错误"
        return False, f"请求失败: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "无法连接到服务器，请检查网络"
    except Exception as e:
        return False, f"连接失败: {str(e)}"


def register_user(phone: str, password: str, name: str, role: str, emergency_contact: str = "") -> tuple:
    """调用后端注册 API"""
    try:
        response = requests.post(
            f"{API_BASE}/api/auth/register",
            json={
                "phone": phone,
                "password": password,
                "name": name,
                "role": role,
                "emergency_contact": emergency_contact
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                user_data = data['data']
                st.session_state['token'] = user_data['token']
                st.session_state['user'] = user_data['user']
                st.session_state['bindings'] = user_data.get('bindings', [])
                st.session_state['authenticated'] = True
                return True, "注册成功"
            return False, data.get('message', '注册失败')
        return False, f"请求失败: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "无法连接到服务器，请检查网络"
    except Exception as e:
        return False, f"连接失败: {str(e)}"


def get_current_user() -> Optional[Dict]:
    """获取当前登录用户"""
    if 'user' in st.session_state and st.session_state.get('authenticated'):
        return st.session_state['user']
    return None


def get_token() -> str:
    return st.session_state.get('token', '')


def is_authenticated() -> bool:
    return st.session_state.get('authenticated', False)


def get_user_role() -> str:
    """获取当前用户角色"""
    user = get_current_user()
    return user.get('role', 'family') if user else 'family'


def get_user_name() -> str:
    """获取当前用户姓名"""
    user = get_current_user()
    return user.get('name', '用户') if user else '用户'


def get_user_phone() -> str:
    """获取当前用户手机号"""
    user = get_current_user()
    return user.get('phone', '') if user else ''


def get_emergency_contact() -> str:
    """获取紧急联系人"""
    user = get_current_user()
    return user.get('emergency_contact', '') if user else ''


def logout():
    """登出"""
    for key in ['token', 'user', 'bindings', 'authenticated']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.clear()


def require_auth(func: Callable) -> Callable:
    """登录验证装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.error("🔒 请先登录系统")
            st.stop()
            return None
        return func(*args, **kwargs)
    return wrapper


def validate_phone(phone: str) -> bool:
    """验证手机号是否为11位数字"""
    return phone.isdigit() and len(phone) == 11