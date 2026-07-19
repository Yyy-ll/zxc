# admin/admin.py
import streamlit as st
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import json
from decimal import Decimal

# ========== 添加当前目录到路径 ==========
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ========== 页面配置 ==========
st.set_page_config(
    page_title="管理面板 - 银龄安居",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 导入工具模块 ==========
from utils.auth import is_admin, logout, login
from utils.database import execute_query, execute_update


# ============================================================
# JSON 序列化辅助函数
# ============================================================
def convert_to_serializable(obj):
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [convert_to_serializable(item) for item in obj]
    else:
        return obj


# ============================================================
# 获取数据函数
# ============================================================
def get_admin_data():
    """获取管理面板所有数据"""
    stats_sql = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = '待处理' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = '处理中' THEN 1 ELSE 0 END) as processing,
            SUM(CASE WHEN status = '已处理' THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN status = '已忽略' THEN 1 ELSE 0 END) as ignored,
            COUNT(DISTINCT username) as unique_users
        FROM feedback
    """
    stats = execute_query(stats_sql)
    stats = stats[0] if stats else {}

    sql = """
        SELECT * FROM feedback 
        ORDER BY CASE WHEN status = '待处理' THEN 0 WHEN status = '处理中' THEN 1 ELSE 2 END, created_at DESC
    """
    feedbacks = execute_query(sql)

    stats = convert_to_serializable(stats)
    feedbacks = convert_to_serializable(feedbacks)

    return {
        'stats': stats,
        'feedbacks': feedbacks,
        'total': len(feedbacks) if feedbacks else 0
    }


# ============================================================
# 登录页面
# ============================================================
def show_login_page():
    """显示登录界面"""
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.1);
            text-align: center;
        }
        .login-title {
            font-size: 28px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 8px;
        }
        .login-subtitle {
            color: #64748b;
            margin-bottom: 30px;
        }
        .login-logo {
            font-size: 48px;
            margin-bottom: 16px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="login-container">
        <div class="login-logo">🛠️</div>
        <div class="login-title">管理面板</div>
        <div class="login-subtitle">银龄安居 - 跌倒风险预警系统</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("👤 用户名", placeholder="请输入用户名")
        password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
        submitted = st.form_submit_button("登录", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("⚠️ 请输入用户名和密码")
            elif login(username, password):
                st.success("✅ 登录成功！")
                st.rerun()
            else:
                st.error("❌ 用户名或密码错误")

    st.caption("💡 默认管理员账号: admin / admin123")


# ============================================================
# 主函数
# ============================================================
def main():
    """管理面板主入口"""

    if not st.session_state.get('authenticated', False):
        show_login_page()
        return

    if not is_admin():
        st.error("❌ 您没有访问管理面板的权限")
        st.info("请使用管理员账号登录")
        if st.button("重新登录", key="relogin_btn"):
            logout()
            st.rerun()
        return

    # ============================================================
    # 获取数据
    # ============================================================
    data = get_admin_data()
    initial_data_json = json.dumps(data, ensure_ascii=False)

    # ============================================================
    # 构建 HTML - 完全无白边
    # ============================================================
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{
                height: 100%;
                margin: 0;
                padding: 0;
                background: #f1f5f9;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                min-height: 100vh;
                padding: 0;
            }}
            .app-container {{
                display: grid;
                grid-template-columns: 220px 1fr;
                min-height: 100vh;
                gap: 0;
                background: #f1f5f9;
            }}

            /* ===== 侧边栏 ===== */
            .sidebar {{
                background: white;
                padding: 20px 16px;
                border-right: 1px solid #e5e7eb;
                min-height: 100vh;
                position: sticky;
                top: 0;
                overflow-y: auto;
                height: 100vh;
            }}
            .sidebar .logo {{
                font-size: 18px;
                font-weight: 700;
                color: #1e293b;
                display: flex;
                align-items: center;
                gap: 8px;
                padding-bottom: 14px;
                border-bottom: 1px solid #e5e7eb;
            }}
            .sidebar .logo span {{ font-size: 22px; }}
            .sidebar .user-info {{
                background: #f8fafc;
                padding: 12px 14px;
                border-radius: 10px;
                margin: 14px 0;
            }}
            .sidebar .user-info .name {{
                font-weight: 600;
                color: #1e293b;
                font-size: 14px;
            }}
            .sidebar .user-info .time {{
                font-size: 12px;
                color: #94a3b8;
                margin-top: 2px;
            }}
            .sidebar .divider {{
                border: none;
                border-top: 1px solid #e5e7eb;
                margin: 10px 0;
            }}
            .sidebar .menu-label {{
                font-size: 11px;
                font-weight: 600;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 6px;
            }}
            .sidebar .menu-btn {{
                display: flex;
                align-items: center;
                gap: 10px;
                width: 100%;
                padding: 8px 14px;
                border: none;
                border-radius: 8px;
                background: transparent;
                color: #64748b;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                margin-bottom: 2px;
            }}
            .sidebar .menu-btn:hover {{ background: #f1f5f9; }}
            .sidebar .menu-btn.active {{
                background: #2563eb;
                color: white;
            }}
            .sidebar .menu-btn .icon {{ font-size: 16px; }}
            .sidebar .logout-btn {{
                display: flex;
                align-items: center;
                gap: 10px;
                width: 100%;
                padding: 8px 14px;
                border: none;
                border-radius: 8px;
                background: #fef2f2;
                color: #dc2626;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                margin-top: 4px;
            }}
            .sidebar .logout-btn:hover {{ background: #fee2e2; }}

            /* ===== 主内容 ===== */
            .main-content {{
                padding: 0 24px 0 24px;
                background: #f1f5f9;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }}

            /* 头部 */
            .page-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 0 12px 0;
                border-bottom: 3px solid #2563eb;
                margin-bottom: 16px;
                flex-wrap: wrap;
                gap: 10px;
                background: #f1f5f9;
            }}
            .page-header .left {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .page-header .left h1 {{
                font-size: 24px;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
            }}
            .page-header .left .icon {{ font-size: 26px; }}
            .page-header .right {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .page-header .update-time {{
                font-size: 13px;
                color: #94a3b8;
            }}

            .ws-status {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                padding: 4px 14px;
                border-radius: 20px;
                background: #dcfce7;
                color: #166534;
            }}
            .ws-status .dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #22c55e;
                display: inline-block;
                animation: pulse 2s infinite;
            }}
            .ws-status.offline {{
                background: #fee2e2;
                color: #991b1b;
            }}
            .ws-status.offline .dot {{
                background: #ef4444;
                animation: none;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; transform: scale(1); }}
                50% {{ opacity: 0.3; transform: scale(0.8); }}
            }}

            .page {{ display: none; }}
            .page.active {{ display: block; }}

            /* ===== 统计卡片 ===== */
            .stats-row {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 12px;
                margin-bottom: 16px;
            }}
            .stat-card {{
                background: white;
                padding: 16px 12px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid #e5e7eb;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.3s ease;
            }}
            .stat-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.10);
                border-color: #93c5fd;
            }}
            .stat-card .number {{
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
            }}
            .stat-card .number.pending {{ color: #ef4444; }}
            .stat-card .number.orange {{ color: #f97316; }}
            .stat-card .number.green {{ color: #16a34a; }}
            .stat-card .number.blue {{ color: #2563eb; }}
            .stat-card .label {{
                font-size: 13px;
                color: #64748b;
                margin-top: 4px;
            }}

            /* ===== 内容卡片 ===== */
            .content-card {{
                background: white;
                padding: 18px 20px;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                margin-bottom: 15px;
                border: 1px solid #e5e7eb;
            }}
            .content-card .card-title {{
                font-weight: 600;
                color: #1e293b;
                margin-bottom: 12px;
                font-size: 15px;
            }}

            /* ===== 反馈卡片 ===== */
            .feedback-card {{
                background: white;
                border-radius: 10px;
                padding: 12px 16px;
                margin-bottom: 8px;
                border: 1px solid #e5e7eb;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.3s ease;
            }}
            .feedback-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.10);
                border-color: #93c5fd;
            }}
            .feedback-card .top {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 8px;
                cursor: pointer;
            }}
            .feedback-card .top .left {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .feedback-card .top .id {{
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                font-family: 'Courier New', monospace;
            }}
            .feedback-card .top .type {{
                font-size: 14px;
                color: #1e293b;
                font-weight: 500;
            }}
            .feedback-card .top .user {{
                font-size: 13px;
                color: #64748b;
            }}

            .status-badge {{
                display: inline-block;
                padding: 2px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            .status-pending {{ background: #fef3c7; color: #92400e; }}
            .status-processing {{ background: #dbeafe; color: #1e40af; }}
            .status-resolved {{ background: #dcfce7; color: #166534; }}
            .status-ignored {{ background: #f1f5f9; color: #64748b; }}

            .feedback-card .detail {{
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid #f1f5f9;
                display: none;
            }}
            .feedback-card .detail .row {{
                display: flex;
                padding: 3px 0;
                font-size: 14px;
                color: #475569;
                flex-wrap: wrap;
            }}
            .feedback-card .detail .label {{
                color: #94a3b8;
                font-weight: 500;
                min-width: 85px;
            }}

            .action-form {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid #e5e7eb;
            }}
            .action-form select,
            .action-form textarea {{
                width: 100%;
                padding: 6px 10px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 13px;
                background: white;
            }}
            .action-form textarea {{ min-height: 50px; resize: vertical; }}
            .action-form .btn-group {{
                grid-column: 1/3;
                text-align: right;
            }}
            .btn-handle {{
                background: #16a34a;
                color: white;
                border: none;
                padding: 6px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s;
            }}
            .btn-handle:hover {{ background: #15803d; }}

            /* ===== 图表 ===== */
            .charts-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }}
            .chart-box {{
                background: white;
                padding: 18px 20px;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }}
            .chart-box .title {{
                font-weight: 600;
                color: #1e293b;
                margin-bottom: 12px;
                font-size: 14px;
            }}
            .chart-bar {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 4px;
            }}
            .chart-bar .label {{
                min-width: 70px;
                font-size: 13px;
                color: #64748b;
            }}
            .chart-bar .bar {{
                height: 24px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: flex-end;
                padding-right: 10px;
                color: white;
                font-size: 12px;
                font-weight: 500;
                min-width: 40px;
                transition: width 0.3s;
            }}
            .chart-bar .bar.blue {{ background: #2563eb; }}
            .chart-bar .bar.orange {{ background: #f97316; }}
            .chart-bar .bar.green {{ background: #22c55e; }}
            .chart-bar .bar.red {{ background: #ef4444; }}

            .empty-state {{
                text-align: center;
                padding: 40px 20px;
                color: #94a3b8;
            }}
            .empty-state .icon {{ font-size: 48px; margin-bottom: 8px; }}
            .empty-state .title {{ font-size: 16px; font-weight: 600; color: #475569; }}

            .toast {{
                padding: 12px 16px;
                border-radius: 8px;
                display: none;
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 999;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
            .toast.success {{ display: block; background: #dcfce7; color: #166534; border: 1px solid #86efac; }}
            .toast.error {{ display: block; background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }}

            .footer-bar {{
                display: flex;
                justify-content: space-between;
                padding: 10px 16px;
                background: white;
                border-radius: 10px;
                margin-top: 15px;
                margin-bottom: 16px;
                font-size: 13px;
                color: #64748b;
                border: 1px solid #e5e7eb;
                flex-wrap: wrap;
                gap: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }}

            @media (max-width: 992px) {{
                .app-container {{ grid-template-columns: 1fr; }}
                .sidebar {{ height: auto; position: static; border-right: none; border-bottom: 1px solid #e5e7eb; min-height: auto; }}
                .stats-row {{ grid-template-columns: repeat(3, 1fr); }}
                .charts-grid {{ grid-template-columns: 1fr; }}
                .main-content {{ padding: 0 16px; }}
            }}
            @media (max-width: 768px) {{
                .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
                .action-form {{ grid-template-columns: 1fr; }}
                .action-form .btn-group {{ grid-column: 1; }}
                .page-header .left h1 {{ font-size: 20px; }}
                .main-content {{ padding: 0 12px; }}
            }}
            @media (max-width: 480px) {{
                .stats-row {{ grid-template-columns: 1fr; }}
                .feedback-card .top .left {{ flex-direction: column; align-items: flex-start; }}
                .sidebar {{ padding: 16px 12px; }}
                .main-content {{ padding: 0 8px; }}
            }}
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- 侧边栏 -->
            <div class="sidebar">
                <div class="logo"><span>🛠️</span> 管理面板</div>
                <div class="user-info">
                    <div class="name">👤 {st.session_state.get('name', '管理员')}</div>
                    <div class="time">登录: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
                </div>
                <hr class="divider">
                <div class="menu-label">功能菜单</div>
                <button class="menu-btn active" data-page="dashboard" onclick="switchPage('dashboard')">
                    <span class="icon">📊</span> 概览
                </button>
                <button class="menu-btn" data-page="feedback" onclick="switchPage('feedback')">
                    <span class="icon">📋</span> 反馈管理
                </button>
                <button class="menu-btn" data-page="stats" onclick="switchPage('stats')">
                    <span class="icon">📈</span> 统计分析
                </button>
                <hr class="divider">
                <button class="logout-btn" onclick="logout()">
                    <span>🚪</span> 退出登录
                </button>
            </div>

            <!-- 主内容 -->
            <div class="main-content">
                <!-- 头部 -->
                <div class="page-header">
                    <div class="left">
                        <span class="icon" id="page-icon">📊</span>
                        <h1 id="page-title">概览</h1>
                    </div>
                    <div class="right">
                        <span class="update-time">🕐 <span id="update-time">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></span>
                        <span id="ws-status" class="ws-status">
                            <span class="dot"></span>
                            <span>已连接</span>
                        </span>
                    </div>
                </div>

                <div id="toast" class="toast"></div>

                <!-- 页面：概览 -->
                <div id="page-dashboard" class="page active">
                    <div class="stats-row">
                        <div class="stat-card">
                            <div class="number blue" id="stat-total">0</div>
                            <div class="label">📋 总反馈</div>
                        </div>
                        <div class="stat-card">
                            <div class="number pending" id="stat-pending">0</div>
                            <div class="label">⏳ 待处理</div>
                        </div>
                        <div class="stat-card">
                            <div class="number orange" id="stat-processing">0</div>
                            <div class="label">🔄 处理中</div>
                        </div>
                        <div class="stat-card">
                            <div class="number green" id="stat-resolved">0</div>
                            <div class="label">✅ 已处理</div>
                        </div>
                        <div class="stat-card">
                            <div class="number blue" id="stat-users">0</div>
                            <div class="label">👤 反馈用户</div>
                        </div>
                    </div>

                    <div class="content-card">
                        <div class="card-title">📋 最新反馈（待处理优先）</div>
                        <div id="recent-list"></div>
                    </div>
                </div>

                <!-- 页面：反馈管理 -->
                <div id="page-feedback" class="page">
                    <div style="margin-bottom:12px;color:#64748b;font-size:14px;">
                        共 <span id="fb-total">0</span> 条记录
                    </div>
                    <div id="feedback-list"></div>
                </div>

                <!-- 页面：统计分析 -->
                <div id="page-stats" class="page">
                    <div class="stats-row" style="grid-template-columns:repeat(4,1fr);">
                        <div class="stat-card">
                            <div class="number blue" id="stats-total">0</div>
                            <div class="label">总反馈</div>
                        </div>
                        <div class="stat-card">
                            <div class="number blue" id="stats-users">0</div>
                            <div class="label">反馈用户数</div>
                        </div>
                        <div class="stat-card">
                            <div class="number green" id="stats-rate">0%</div>
                            <div class="label">处理率</div>
                        </div>
                        <div class="stat-card">
                            <div class="number pending" id="stats-pending">0</div>
                            <div class="label">待处理</div>
                        </div>
                    </div>

                    <div class="charts-grid">
                        <div class="chart-box">
                            <div class="title">📊 按反馈类型统计</div>
                            <div id="type-stats-chart"></div>
                        </div>
                        <div class="chart-box">
                            <div class="title">📊 按状态统计</div>
                            <div id="status-stats-chart"></div>
                        </div>
                    </div>
                </div>

                <!-- 底部 -->
                <div class="footer-bar">
                    <span>🛠️ 银龄安居 - 管理面板</span>
                    <span id="footer-status">系统运行正常</span>
                </div>
            </div>
        </div>

        <script>
            const INITIAL_DATA = {initial_data_json};
            const API_BASE = 'http://localhost:8001';
            const WS_URL = 'ws://localhost:8766';

            let allFeedbacks = INITIAL_DATA.feedbacks || [];
            let stats = INITIAL_DATA.stats || {{}};
            let ws = null;
            let isConnected = false;
            let reconnectTimer = null;

            const pageTitles = {{
                'dashboard': {{ icon: '📊', title: '概览' }},
                'feedback': {{ icon: '📋', title: '反馈管理' }},
                'stats': {{ icon: '📈', title: '统计分析' }}
            }};

            function updateStatus(connected) {{
                const el = document.getElementById('ws-status');
                if (!el) return;
                if (connected) {{
                    el.className = 'ws-status';
                    el.innerHTML = '<span class="dot"></span><span>已连接</span>';
                }} else {{
                    el.className = 'ws-status offline';
                    el.innerHTML = '<span class="dot"></span><span>已断开</span>';
                }}
                isConnected = connected;
            }}

            function connectWebSocket() {{
                try {{
                    console.log('🔗 连接管理面板 WebSocket...');
                    ws = new WebSocket(WS_URL);
                    ws.onopen = function() {{
                        console.log('✅ 管理面板 WebSocket 已连接');
                        updateStatus(true);
                        ws.send(JSON.stringify({{ type: 'subscribe', channel: 'feedback' }}));
                    }};
                    ws.onmessage = function(event) {{
                        try {{
                            const data = JSON.parse(event.data);
                            console.log('📩 收到推送:', data);
                            if (data.type === 'feedback_update') {{
                                console.log('🔄 反馈数据更新');
                                loadAllData();
                            }}
                        }} catch(e) {{
                            console.error('解析消息失败:', e);
                        }}
                    }};
                    ws.onclose = function() {{
                        console.log('❌ 管理面板 WebSocket 断开');
                        updateStatus(false);
                        if (reconnectTimer) clearTimeout(reconnectTimer);
                        reconnectTimer = setTimeout(connectWebSocket, 3000);
                    }};
                    ws.onerror = function(error) {{
                        console.error('WebSocket 错误:', error);
                    }};
                }} catch(e) {{
                    console.error('连接失败:', e);
                    updateStatus(false);
                    if (reconnectTimer) clearTimeout(reconnectTimer);
                    reconnectTimer = setTimeout(connectWebSocket, 3000);
                }}
            }}

            function loadAllData() {{
                fetch(API_BASE + '/api/admin/data')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            allFeedbacks = data.feedbacks || [];
                            stats = data.stats || {{}};
                            renderAll();
                            document.getElementById('update-time').textContent = new Date().toLocaleString('zh-CN');
                        }}
                    }})
                    .catch(error => console.error('加载数据失败:', error));
            }}

            function renderAll() {{
                renderDashboard();
                renderFeedbackList();
                renderStats();
            }}

            function renderDashboard() {{
                document.getElementById('stat-total').textContent = stats.total || 0;
                document.getElementById('stat-pending').textContent = stats.pending || 0;
                document.getElementById('stat-processing').textContent = stats.processing || 0;
                document.getElementById('stat-resolved').textContent = stats.resolved || 0;
                document.getElementById('stat-users').textContent = stats.unique_users || 0;

                const container = document.getElementById('recent-list');
                const recent = allFeedbacks.slice(0, 10);
                if (!recent || recent.length === 0) {{
                    container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div class="title">暂无数据</div></div>';
                    return;
                }}

                const statusMap = {{
                    '待处理': 'status-pending',
                    '处理中': 'status-processing',
                    '已处理': 'status-resolved',
                    '已忽略': 'status-ignored'
                }};

                let html = '';
                recent.forEach(fb => {{
                    const cls = statusMap[fb.status] || 'status-pending';
                    html += `
                        <div class="feedback-card">
                            <div class="top" onclick="toggleDetail(this.closest('.feedback-card').querySelector('.detail'))">
                                <div class="left">
                                    <span class="id">#${{fb.id}}</span>
                                    <span class="type">${{fb.feedback_type || '未知'}}</span>
                                    <span class="user">${{fb.username || '未知'}}</span>
                                </div>
                                <span class="status-badge ${{cls}}">${{fb.status || '待处理'}}</span>
                            </div>
                            <div class="detail">
                                <div class="row"><span class="label">📝 描述：</span>${{fb.description || '无描述'}}</div>
                                <div class="row"><span class="label">📅 提交时间：</span>${{fb.created_at || '未知'}}</div>
                            </div>
                        </div>
                    `;
                }});
                container.innerHTML = html;
            }}

            function toggleDetail(el) {{
                if (el) {{
                    el.style.display = el.style.display === 'none' || el.style.display === '' ? 'block' : 'none';
                }}
            }}

            function renderFeedbackList() {{
                const container = document.getElementById('feedback-list');
                const totalEl = document.getElementById('fb-total');
                totalEl.textContent = allFeedbacks.length;

                if (!allFeedbacks || allFeedbacks.length === 0) {{
                    container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div class="title">暂无反馈记录</div></div>';
                    return;
                }}

                const statusMap = {{
                    '待处理': 'status-pending',
                    '处理中': 'status-processing',
                    '已处理': 'status-resolved',
                    '已忽略': 'status-ignored'
                }};

                let html = '';
                allFeedbacks.forEach(fb => {{
                    const cls = statusMap[fb.status] || 'status-pending';
                    html += `
                        <div class="feedback-card" id="fb-${{fb.id}}">
                            <div class="top" onclick="toggleDetail(this.closest('.feedback-card').querySelector('.detail'))">
                                <div class="left">
                                    <span class="id">#${{fb.id}}</span>
                                    <span class="type">${{fb.feedback_type || '未知'}}</span>
                                    <span class="user">${{fb.username || '未知'}}</span>
                                </div>
                                <span class="status-badge ${{cls}}">${{fb.status || '待处理'}}</span>
                            </div>
                            <div class="detail">
                                <div class="row"><span class="label">👤 用户：</span>${{fb.username || '未知'}}</div>
                                <div class="row"><span class="label">📋 类型：</span>${{fb.feedback_type || '未知'}}</div>
                                <div class="row"><span class="label">📝 描述：</span>${{fb.description || '无描述'}}</div>
                                <div class="row"><span class="label">📅 事件时间：</span>${{fb.event_time || '未知'}}</div>
                                ${{fb.notes ? `<div class="row"><span class="label">💬 备注：</span>${{fb.notes}}</div>` : ''}}
                                <div class="action-form">
                                    <div>
                                        <label style="font-size:13px;color:#64748b;font-weight:500;">更新状态</label>
                                        <select id="status-${{fb.id}}">
                                            <option value="待处理" ${{fb.status === '待处理' ? 'selected' : ''}}>待处理</option>
                                            <option value="处理中" ${{fb.status === '处理中' ? 'selected' : ''}}>处理中</option>
                                            <option value="已处理" ${{fb.status === '已处理' ? 'selected' : ''}}>已处理</option>
                                            <option value="已忽略" ${{fb.status === '已忽略' ? 'selected' : ''}}>已忽略</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label style="font-size:13px;color:#64748b;font-weight:500;">处理内容</label>
                                        <textarea id="notes-${{fb.id}}" placeholder="请填写处理结果...">${{fb.notes || ''}}</textarea>
                                    </div>
                                    <div class="btn-group">
                                        <button class="btn-handle" onclick="handleFeedback(${{fb.id}})">✅ 确认处理</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }});
                container.innerHTML = html;
            }}

            function handleFeedback(id) {{
                const status = document.getElementById('status-' + id).value;
                const notes = document.getElementById('notes-' + id).value.trim();

                if (!notes) {{
                    showToast('error', '⚠️ 请输入处理内容');
                    return;
                }}

                const data = {{ id: id, status: status, notes: notes, handled_by: '管理员' }};

                fetch(API_BASE + '/api/admin/handle_feedback', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }})
                .then(response => response.json())
                .then(result => {{
                    if (result.status === 'success') {{
                        showToast('success', '✅ 反馈已处理');
                        loadAllData();
                    }} else {{
                        showToast('error', '❌ 处理失败: ' + result.message);
                    }}
                }})
                .catch(error => showToast('error', '❌ 处理失败: ' + error));
            }}

            window.handleFeedback = handleFeedback;

            function renderStats() {{
                const total = allFeedbacks.length;
                const resolved = allFeedbacks.filter(f => f.status === '已处理').length;
                const pending = allFeedbacks.filter(f => f.status === '待处理').length;
                const users = new Set(allFeedbacks.map(f => f.username)).size;
                const rate = total > 0 ? Math.round(resolved / total * 100) : 0;

                document.getElementById('stats-total').textContent = total;
                document.getElementById('stats-users').textContent = users;
                document.getElementById('stats-rate').textContent = rate + '%';
                document.getElementById('stats-pending').textContent = pending;

                const typeMap = {{}};
                allFeedbacks.forEach(f => {{
                    const t = f.feedback_type || '其他';
                    typeMap[t] = (typeMap[t] || 0) + 1;
                }});
                renderBarChart('type-stats-chart', typeMap, {{}});

                const statusMap = {{'待处理':0, '处理中':0, '已处理':0, '已忽略':0}};
                allFeedbacks.forEach(f => {{
                    const s = f.status || '待处理';
                    if (statusMap[s] !== undefined) statusMap[s]++;
                }});
                const statusColors = {{'待处理':'#ef4444', '处理中':'#f97316', '已处理':'#22c55e', '已忽略':'#94a3b8'}};
                renderBarChart('status-stats-chart', statusMap, statusColors);
            }}

            function renderBarChart(containerId, data, colors) {{
                const container = document.getElementById(containerId);
                const entries = Object.entries(data).filter(([k,v]) => v > 0);

                if (entries.length === 0) {{
                    container.innerHTML = '<div style="text-align:center;padding:20px;color:#94a3b8;">暂无数据</div>';
                    return;
                }}

                const maxVal = Math.max(...entries.map(([k,v]) => v));
                let html = '';
                entries.forEach(([key, value]) => {{
                    const pct = maxVal > 0 ? Math.round(value / maxVal * 100) : 0;
                    const color = colors && colors[key] ? colors[key] : '#2563eb';
                    const cls = color === '#2563eb' ? 'blue' : color === '#f97316' ? 'orange' : color === '#22c55e' ? 'green' : 'red';
                    html += `
                        <div class="chart-bar">
                            <span class="label">${{key}}</span>
                            <div class="bar ${{cls}}" style="width:${{Math.max(40, pct)}}%;background:${{color}};">${{value}}</div>
                        </div>
                    `;
                }});
                container.innerHTML = html;
            }}

            function switchPage(page) {{
                document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
                document.getElementById('page-' + page).classList.add('active');

                document.querySelectorAll('.menu-btn').forEach(el => el.classList.remove('active'));
                document.querySelector(`[data-page="${{page}}"]`).classList.add('active');

                const info = pageTitles[page] || {{ icon: '📊', title: '概览' }};
                document.getElementById('page-icon').textContent = info.icon;
                document.getElementById('page-title').textContent = info.title;
            }}

            window.switchPage = switchPage;

            function logout() {{
                if (confirm('确定要退出登录吗？')) {{
                    window.parent.location.reload();
                }}
            }}

            window.logout = logout;

            function showToast(type, message) {{
                const el = document.getElementById('toast');
                el.className = 'toast ' + type;
                el.textContent = message;
                el.style.display = 'block';
                setTimeout(() => el.style.display = 'none', 5000);
            }}

            function init() {{
                renderAll();
                setTimeout(connectWebSocket, 500);
                console.log('🚀 管理面板已加载');
            }}

            if (document.readyState === 'complete') {{
                init();
            }} else {{
                window.addEventListener('load', init);
            }}

            document.addEventListener('visibilitychange', function() {{
                if (!document.hidden && !isConnected) {{
                    console.log('👁️ 页面可见，重连 WebSocket...');
                    connectWebSocket();
                }}
            }});
        </script>
    </body>
    </html>
    """

    st.components.v1.html(
        html_content,
        height=1100,
        scrolling=True
    )


if __name__ == "__main__":
    main()