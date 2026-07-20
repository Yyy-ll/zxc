# pages/feedback.py
import streamlit as st
import json
from datetime import datetime, timedelta
from decimal import Decimal
from utils.auth import require_auth, get_current_user
from utils.feedback_dao import get_feedback_list, save_feedback


@require_auth
def main():
    user = get_current_user()

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

    all_feedbacks = get_feedback_list(limit=100)
    current_username = user['username']
    user_feedbacks = []
    if all_feedbacks:
        user_feedbacks = [fb for fb in all_feedbacks if fb.get('username') == current_username]

    all_feedbacks = convert_to_serializable(all_feedbacks)
    user_feedbacks = convert_to_serializable(user_feedbacks)

    today = datetime.now().date()
    min_date = today - timedelta(days=14)
    max_date = today

    initial_data = {
        'all': all_feedbacks,
        'user': user_feedbacks,
        'username': current_username,
        'total': len(all_feedbacks) if all_feedbacks else 0,
        'user_total': len(user_feedbacks) if user_feedbacks else 0,
        'min_date': min_date.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d')
    }

    initial_data_json = json.dumps(initial_data, ensure_ascii=False)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f1f5f9;
                padding: 0;
                min-height: 100vh;
            }}
            .app-container {{
                padding: 16px 20px 30px 20px;
                max-width: 1200px;
                margin: 0 auto;
            }}

            /* ===== 头部 ===== */
            .page-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 0 12px 0;
                border-bottom: 3px solid #f97316;
                margin-bottom: 16px;
                flex-wrap: wrap;
                gap: 10px;
            }}
            .page-header h1 {{
                font-size: 26px;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
            }}
            .page-header .icon {{ font-size: 28px; }}

            .ws-status {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                padding: 4px 12px;
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

            /* ===== Tabs ===== */
            .tabs {{
                display: flex;
                gap: 4px;
                margin-bottom: 20px;
                background: white;
                padding: 4px;
                border-radius: 10px;
                border: 1px solid #e5e7eb;
            }}
            .tab {{
                flex: 1;
                padding: 10px 16px;
                text-align: center;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                font-size: 14px;
                color: #64748b;
                transition: all 0.2s;
                border: none;
                background: none;
            }}
            .tab.active {{ background: #2563eb; color: white; }}
            .tab:hover:not(.active) {{ background: #f1f5f9; }}
            .tab-content {{ display: block; }}
            .tab-content.hidden {{ display: none; }}

            /* ===== 表单 ===== */
            .content-card {{
                background: white;
                padding: 20px 24px;
                border-radius: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                margin-bottom: 15px;
                border: 1px solid #e5e7eb;
            }}
            .content-card .card-title {{
                font-weight: 600;
                color: #1e293b;
                margin-bottom: 16px;
                font-size: 16px;
            }}
            .form-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }}
            .form-group {{ margin-bottom: 16px; }}
            .form-group label {{
                display: block;
                font-size: 14px;
                font-weight: 500;
                color: #1e293b;
                margin-bottom: 4px;
            }}
            .form-group input,
            .form-group select,
            .form-group textarea {{
                width: 100%;
                padding: 10px 14px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                background: white;
                transition: border-color 0.2s;
            }}
            .form-group textarea {{ min-height: 120px; resize: vertical; }}
            .form-group input:focus,
            .form-group select:focus,
            .form-group textarea:focus {{
                outline: none;
                border-color: #2563eb;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
            }}

            .btn-submit {{
                background: #2563eb;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: background 0.2s;
            }}
            .btn-submit:hover {{ background: #1d4ed8; }}

            .date-hint {{
                font-size: 12px;
                color: #94a3b8;
                margin-top: 4px;
                padding: 4px 12px;
                background: #f8fafc;
                border-radius: 6px;
                border: 1px dashed #e2e8f0;
            }}
            .date-hint span {{ font-weight: 600; color: #475569; }}

            /* ===== 统计卡片 ===== */
            .stats-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                margin-bottom: 20px;
            }}
            .stat-card {{
                background: white;
                padding: 18px 16px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid #e5e7eb;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.3s ease;
            }}
            .stat-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.10);
                border-color: #93c5fd;
            }}
            .stat-number {{
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
            }}
            .stat-label {{
                font-size: 13px;
                color: #64748b;
                margin-top: 4px;
            }}

            /* ===== 反馈列表 ===== */
            .feedback-item {{
                background: white;
                border-radius: 12px;
                padding: 14px 18px;
                margin-bottom: 10px;
                border: 1px solid #e5e7eb;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }}
            .feedback-item:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.10);
                border-color: #93c5fd;
            }}
            .feedback-item .row {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 8px;
            }}
            .feedback-item .left {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .feedback-item .date {{
                color: #94a3b8;
                font-size: 13px;
                font-weight: 500;
                font-family: 'Courier New', monospace;
            }}
            .feedback-item .type {{
                font-size: 14px;
                color: #1e293b;
                font-weight: 500;
            }}
            .status-badge {{
                display: inline-block;
                padding: 3px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            .status-pending {{ background: #fef3c7; color: #92400e; }}
            .status-processing {{ background: #dbeafe; color: #1e40af; }}
            .status-resolved {{ background: #dcfce7; color: #166534; }}
            .status-ignored {{ background: #f1f5f9; color: #64748b; }}

            .feedback-item .detail {{
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid #f1f5f9;
                display: none;
                font-size: 14px;
                color: #475569;
            }}
            .feedback-item .detail .label {{
                color: #94a3b8;
                font-weight: 500;
                min-width: 80px;
                display: inline-block;
            }}
            .feedback-item .detail .line {{
                padding: 4px 0;
            }}

            .toast {{
                padding: 12px 16px;
                border-radius: 8px;
                margin-bottom: 16px;
                display: none;
            }}
            .toast.success {{
                display: block;
                background: #dcfce7;
                color: #166534;
                border: 1px solid #86efac;
            }}
            .toast.error {{
                display: block;
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fca5a5;
            }}

            .empty-state {{
                text-align: center;
                padding: 60px 20px;
                color: #94a3b8;
            }}
            .empty-state .icon {{ font-size: 56px; margin-bottom: 12px; }}
            .empty-state .title {{ font-size: 18px; font-weight: 600; color: #475569; }}

            @media (max-width: 768px) {{
                .form-row {{ grid-template-columns: 1fr; }}
                .page-header h1 {{ font-size: 20px; }}
                .stats-row {{ grid-template-columns: 1fr; }}
                .app-container {{ padding: 10px; }}
                .feedback-item .row {{ flex-direction: column; align-items: flex-start; }}
            }}
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- 头部 -->
            <div class="page-header">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span class="icon">💬</span>
                    <h1>反馈中心</h1>
                </div>
                <span id="ws-status" class="ws-status">
                    <span class="dot"></span>
                    <span>已连接</span>
                </span>
            </div>

            <div id="toast" class="toast"></div>

            <!-- Tabs -->
            <div class="tabs">
                <button class="tab active" data-tab="submit" onclick="switchTab('submit')">📝 提交反馈</button>
                <button class="tab" data-tab="list" onclick="switchTab('list')">📊 我的反馈</button>
            </div>

            <!-- Tab 1 -->
            <div id="tab-submit" class="tab-content">
                <div class="content-card">
                    <div class="card-title">📝 提交反馈</div>
                    <form id="feedbackForm" onsubmit="submitFeedback(event)">
                        <div class="form-row">
                            <div class="form-group">
                                <label>📅 事件发生日期</label>
                                <input type="date" id="eventDate" 
                                       min="{min_date.strftime('%Y-%m-%d')}" 
                                       max="{max_date.strftime('%Y-%m-%d')}"
                                       value="{today.strftime('%Y-%m-%d')}">
                                <div class="date-hint">
                                    📅 可选范围：<span>{min_date.strftime('%Y-%m-%d')}</span> ~ <span>{today.strftime('%Y-%m-%d')}</span>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>📋 反馈类型</label>
                                <select id="feedbackType">
                                    <option value="误报">误报</option>
                                    <option value="漏报">漏报</option>
                                    <option value="延迟报警">延迟报警</option>
                                    <option value="系统异常">系统异常</option>
                                    <option value="其他">其他</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>📝 问题描述</label>
                            <textarea id="description" placeholder="请详细描述您遇到的问题..."></textarea>
                        </div>
                        <button type="submit" class="btn-submit">✅ 提交反馈</button>
                    </form>
                </div>
            </div>

            <!-- Tab 2 -->
            <div id="tab-list" class="tab-content hidden">
                <div class="stats-row">
                    <div class="stat-card">
                        <div class="stat-number" id="total-feedback">0</div>
                        <div class="stat-label">📋 总反馈</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="my-feedback">0</div>
                        <div class="stat-label">👤 我的反馈</div>
                    </div>
                </div>
                <div id="feedback-list"></div>
            </div>
        </div>

        <script>
            const INITIAL_DATA = {initial_data_json};
            const API_BASE ='https://zxc-production-f99b.up.railway.app';
            const WS_URL = 'wss://zxc-production-f99b.up.railway.app/ws/feedback';

            let allFeedbacks = INITIAL_DATA.all || [];
            let userFeedbacks = INITIAL_DATA.user || [];
            let ws = null;
            let isConnected = false;
            let reconnectTimer = null;

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
                    console.log('🔗 连接 Feedback WebSocket...');
                    ws = new WebSocket(WS_URL);
                    ws.onopen = function() {{
                        console.log('✅ Feedback WebSocket 已连接');
                        updateStatus(true);
                        ws.send(JSON.stringify({{ type: 'subscribe', channel: 'feedback' }}));
                    }};
                    ws.onmessage = function(event) {{
                        try {{
                            const data = JSON.parse(event.data);
                            console.log('📩 收到推送:', data);
                            if (data.type === 'feedback_update') {{
                                console.log('🔄 反馈数据更新');
                                loadFeedbackData();
                            }}
                        }} catch(e) {{
                            console.error('解析消息失败:', e);
                        }}
                    }};
                    ws.onclose = function() {{
                        console.log('❌ Feedback WebSocket 断开');
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

            function loadFeedbackData() {{
                fetch(API_BASE + '/api/feedback/user/{current_username}')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            allFeedbacks = data.all_feedbacks || [];
                            userFeedbacks = data.user_feedbacks || [];
                            renderFeedbackList();
                            updateStats();
                        }}
                    }})
                    .catch(error => console.error('加载数据失败:', error));
            }}

            function renderFeedbackList() {{
                const container = document.getElementById('feedback-list');
                if (!container) return;

                if (!userFeedbacks || userFeedbacks.length === 0) {{
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="icon">📭</div>
                            <div class="title">您还没有提交过反馈</div>
                        </div>
                    `;
                    return;
                }}

                const statusMap = {{
                    '待处理': 'status-pending',
                    '处理中': 'status-processing',
                    '已处理': 'status-resolved',
                    '已忽略': 'status-ignored'
                }};

                const emojiMap = {{
                    '待处理': '🟡',
                    '处理中': '🔵',
                    '已处理': '🟢',
                    '已忽略': '⚪'
                }};

                let html = '';
                userFeedbacks.forEach(fb => {{
                    const cls = statusMap[fb.status] || 'status-pending';
                    const emoji = emojiMap[fb.status] || '🟡';
                    const date = fb.created_at ? fb.created_at.substring(0, 10) : '未知';
                    const type = fb.feedback_type || '未知类型';

                    html += `
                        <div class="feedback-item" onclick="toggleDetail(this)">
                            <div class="row">
                                <div class="left">
                                    <span class="date">${{date}}</span>
                                    <span class="type">${{emoji}} ${{type}}</span>
                                </div>
                                <span class="status-badge ${{cls}}">${{fb.status || '待处理'}}</span>
                            </div>
                            <div class="detail">
                                <div class="line"><span class="label">📅 事件时间：</span>${{fb.event_time || '未知'}}</div>
                                <div class="line"><span class="label">📝 描述：</span>${{fb.description || '无描述'}}</div>
                                ${{fb.notes ? `<div class="line"><span class="label">💬 备注：</span>${{fb.notes}}</div>` : ''}}
                                ${{fb.handled_at ? `<div class="line"><span class="label">🕐 处理时间：</span>${{fb.handled_at}}</div>` : ''}}
                            </div>
                        </div>
                    `;
                }});
                container.innerHTML = html;
            }}

            function toggleDetail(el) {{
                const detail = el.querySelector('.detail');
                if (detail) {{
                    detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
                }}
            }}

            function updateStats() {{
                document.getElementById('total-feedback').textContent = allFeedbacks ? allFeedbacks.length : 0;
                document.getElementById('my-feedback').textContent = userFeedbacks ? userFeedbacks.length : 0;
            }}

            function switchTab(tab) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
                document.getElementById('tab-' + tab).classList.remove('hidden');
                document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
                document.querySelector(`[data-tab="${{tab}}"]`).classList.add('active');
            }}

            window.switchTab = switchTab;

            function submitFeedback(e) {{
                e.preventDefault();

                const date = document.getElementById('eventDate').value;
                const type = document.getElementById('feedbackType').value;
                const desc = document.getElementById('description').value.trim();

                if (!desc || desc.length < 5) {{
                    showToast('error', '⚠️ 请详细描述您的问题（至少5个字）');
                    return;
                }}

                const data = {{
                    username: '{current_username}',
                    event_time: date,
                    feedback_type: type,
                    description: desc
                }};

                fetch(API_BASE + '/api/feedback/save', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }})
                .then(response => response.json())
                .then(result => {{
                    if (result.status === 'success') {{
                        showToast('success', '✅ 反馈已提交，感谢您的反馈！');
                        document.getElementById('description').value = '';
                        loadFeedbackData();
                    }} else {{
                        showToast('error', '❌ 提交失败: ' + result.message);
                    }}
                }})
                .catch(error => showToast('error', '❌ 提交失败: ' + error));
            }}

            window.submitFeedback = submitFeedback;

            function showToast(type, message) {{
                const el = document.getElementById('toast');
                el.className = 'toast ' + type;
                el.textContent = message;
                el.style.display = 'block';
                setTimeout(() => el.style.display = 'none', 5000);
            }}

            function init() {{
                renderFeedbackList();
                updateStats();
                setTimeout(connectWebSocket, 500);
                console.log('🚀 Feedback 页面已加载');
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
        height=850,
        scrolling=True
    )


if __name__ == "__main__":
    main()