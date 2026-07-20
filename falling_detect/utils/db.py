# utils/db.py
import requests
import streamlit as st
from datetime import datetime, timedelta
import json

# Railway 后端地址
API_BASE = "https://zxc-production-f99b.up.railway.app"


def get_today_events():
    """从 Railway 后端获取今天的所有事件"""
    try:
        response = requests.get(f"{API_BASE}/api/events/today", timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            # 转换时间格式，兼容前端代码
            for e in events:
                if 'timestamp' in e:
                    try:
                        # 处理 ISO 格式时间
                        if isinstance(e['timestamp'], str):
                            e['timestamp'] = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
                    except:
                        pass
            return events
        else:
            st.error(f"❌ 获取今日事件失败: HTTP {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        st.error("❌ 连接后端超时，请检查网络")
        return []
    except requests.exceptions.ConnectionError:
        st.error("❌ 无法连接到后端，请检查后端是否运行")
        return []
    except Exception as e:
        st.error(f"❌ 获取今日事件失败: {e}")
        return []


def get_events_last_days(days=7):
    """从 Railway 后端获取最近 N 天的事件"""
    try:
        response = requests.get(f"{API_BASE}/api/events/last_days/{days}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            # 转换时间格式
            for e in events:
                if 'timestamp' in e:
                    try:
                        if isinstance(e['timestamp'], str):
                            e['timestamp'] = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
                    except:
                        pass
            return events
        else:
            st.error(f"❌ 获取最近{days}天事件失败: HTTP {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        st.error("❌ 连接后端超时，请检查网络")
        return []
    except requests.exceptions.ConnectionError:
        st.error("❌ 无法连接到后端，请检查后端是否运行")
        return []
    except Exception as e:
        st.error(f"❌ 获取最近{days}天事件失败: {e}")
        return []


def get_all_events():
    """获取所有事件（最近30天）"""
    return get_events_last_days(30)


def get_event_stats():
    """获取事件统计"""
    events = get_today_events()
    stats = {
        'total': len(events),
        'high': len([e for e in events if e.get('level') == '高']),
        'medium': len([e for e in events if e.get('level') == '中']),
        'low': len([e for e in events if e.get('level') == '低'])
    }
    return stats


def save_event(alert_type, level, confidence, source, timestamp=None):
    """保存事件到后端（通过 API）"""
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    data = {
        'type': alert_type,
        'level': level,
        'confidence': confidence,
        'source': source,
        'timestamp': timestamp
    }

    try:
        response = requests.post(
            f"{API_BASE}/api/report",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('event_id')
        else:
            st.error(f"❌ 保存事件失败: HTTP {response.status_code}")
            return None
    except Exception as e:
        st.error(f"❌ 保存事件失败: {e}")
        return None