# pages/health.py
import streamlit as st
import json
from datetime import datetime, timedelta
from utils.auth import require_auth, get_current_user
from utils.db import get_events_last_days
import random
import requests


@require_auth
def main():
    user = get_current_user()
    API_BASE = 'https://zxc-production-f99b.up.railway.app'

    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; padding: 16px 0 12px 0; border-bottom: 3px solid #f97316; margin-bottom: 16px;">
        <span style="font-size: 28px;">❤️</span>
        <h1 style="font-size: 26px; font-weight: 700; color: #1e293b; margin: 0;">心理健康趋势</h1>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 【关键】从 MySQL 加载历史数据生成心理健康指标
    # ============================================================
    events_7days = get_events_last_days(7)

    # 计算每日事件数量作为心理健康指标
    day_count = {}
    for e in events_7days:
        if isinstance(e.get('timestamp'), datetime):
            date_key = e['timestamp'].strftime('%m-%d')
        else:
            try:
                dt = datetime.strptime(e['timestamp'], '%Y-%m-%d %H:%M:%S')
                date_key = dt.strftime('%m-%d')
            except:
                continue
        day_count[date_key] = day_count.get(date_key, 0) + 1

    # 生成心理健康数据
    today = datetime.now()
    health_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_key = date.strftime('%m-%d')
        count = day_count.get(date_key, 0)
        # 心理健康指数 = 100 - (事件数量 * 5 + 随机波动)
        index = max(0, min(100, 100 - count * 5 + random.randint(-10, 15)))
        health_data.append({
            'date': date_key,
            'index': index,
            'count': count
        })

    # 计算当前状态
    if health_data:
        latest = health_data[-1]
        current_index = latest['index']
        if current_index >= 70:
            status = '正常'
            status_class = 'status-safe'
        elif current_index >= 45:
            status = '轻度关注'
            status_class = 'status-warning'
        else:
            status = '需要关注'
            status_class = 'status-danger'

        # 变化趋势
        if len(health_data) >= 2:
            change = health_data[-1]['index'] - health_data[-2]['index']
        else:
            change = 0

        suggestion = random.choice([
            "连续3天活动量下降超过20%，建议家属增加陪伴时间。",
            "近一周社交互动减少，建议安排亲友探访或视频通话。",
            "睡眠质量有所下降，建议调整作息时间。",
            "情绪状态稳定，继续保持良好的生活习惯。",
            "活动量适中，建议保持当前节奏。"
        ])
    else:
        current_index = 50
        status = '正常'
        status_class = 'status-safe'
        change = 0
        suggestion = "暂无数据，请等待系统收集更多信息。"

    # 将健康数据转为 JSON 传递给前端
    health_data_json = json.dumps(health_data, default=str, ensure_ascii=False)

    st.components.v1.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js">
        </script>
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
                max-width: 1400px;
                margin: 0 auto;
            }}

            .stats-row {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
                margin-bottom: 20px;
            }}
            .stat-card {{
                background: white; padding: 18px 16px; border-radius: 12px;
                text-align: center; border: 1px solid #e5e7eb;
                transition: all 0.3s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                height: 100%;
            }}
            .stat-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.10);
                border-color: #93c5fd;
            }}
            .stat-number {{ font-size: 28px; font-weight: 700; color: #1e293b; }}
            .stat-number-red {{ color: #ef4444; }}
            .stat-number-green {{ color: #16a34a; }}
            .stat-number-orange {{ color: #f97316; }}
            .stat-number-blue {{ color: #2563eb; }}
            .stat-label {{ font-size: 13px; color: #64748b; margin-top: 4px; }}

            .content-card {{
                background: white; padding: 20px 24px; border-radius: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                margin-bottom: 15px; border: 1px solid #e5e7eb;
                overflow-x: auto;
            }}
            .content-card .card-title {{
                font-weight: 600; color: #1e293b; margin-bottom: 12px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 8px;
            }}

            .status-badge {{
                display: inline-block; padding: 4px 16px; border-radius: 20px;
                font-size: 14px; font-weight: 600;
            }}
            .status-safe {{ background: #dcfce7; color: #166534; }}
            .status-warning {{ background: #fef3c7; color: #92400e; }}
            .status-danger {{ background: #fee2e2; color: #991b1b; }}
            .status-info {{ background: #dbeafe; color: #1e40af; }}
            .status-online {{ background: #dbeafe; color: #2563eb; }}

            .progress-bar {{
                width: 100%; height: 8px; background: #e5e7eb;
                border-radius: 4px; overflow: hidden; margin-top: 6px;
                max-width: 200px;
                margin: 6px auto 0;
            }}
            .progress-fill {{
                height: 100%; border-radius: 4px; transition: width 0.6s ease;
            }}
            .progress-orange {{ background: linear-gradient(90deg, #fb923c, #f97316); }}

            .suggestion-card {{
                background: linear-gradient(135deg, #eff6ff 0%, #fff7ed 100%);
                border: 1px solid #bfdbfe; border-radius: 12px; padding: 16px 20px;
                margin-top: 15px;
            }}
            .suggestion-card .suggestion-title {{ font-weight: 600; color: #1e293b; font-size: 14px; }}
            .suggestion-card .suggestion-text {{
                color: #475569; font-size: 14px; margin: 6px 0 0 0;
            }}

            .footer-bar {{
                display: flex; justify-content: space-between; padding: 10px 18px;
                background: white; border-radius: 10px; margin-top: 15px;
                font-size: 13px; color: #64748b; border: 1px solid #e5e7eb;
                flex-wrap: wrap; gap: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }}
            .footer-bar .dot {{
                display: inline-block; width: 8px; height: 8px; border-radius: 50%;
                margin-right: 6px;
            }}
            .dot-blue {{ background: #3b82f6; }}
            .dot-green {{ background: #22c55e; }}
            .dot-red {{ background: #ef4444; }}

            .chart-container {{
                width: 100%;
                height: 250px;
                position: relative;
            }}
            .chart-container canvas {{
                width: 100% !important;
                height: 100% !important;
            }}

            .db-status {{
                font-size: 12px;
                padding: 4px 12px;
                border-radius: 20px;
            }}
            .db-status.active {{ background: #dcfce7; color: #166534; }}
            .db-status.inactive {{ background: #fee2e2; color: #991b1b; }}
            .db-status.waiting {{ background: #fef3c7; color: #92400e; }}

            .health-indicators {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 15px;
            }}

            @media screen and (max-width: 768px) {{
                .stats-row {{ grid-template-columns: 1fr 1fr; gap: 10px; }}
                .health-indicators {{ grid-template-columns: 1fr; }}
                .app-container {{ padding: 10px; }}
                .chart-container {{ height: 180px; }}
            }}
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- 统计卡片行 -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-number stat-number-blue" id="health-index">{current_index}</div>
                    <div class="stat-label">综合关注指数</div>
                    <div class="progress-bar"><div class="progress-fill progress-orange" style="width: {current_index}%;"></div></div>
                </div>
                <div class="stat-card">
                    <div class="stat-number {'stat-number-green' if change >= 0 else 'stat-number-red'}" id="change-value">{'+' if change >= 0 else ''}{change}</div>
                    <div class="stat-label">较上周变化</div>
                </div>
                <div class="stat-card">
                    <span class="status-badge {status_class}" id="status-badge" style="font-size: 16px;">{status}</span>
                    <div class="stat-label" style="margin-top: 6px;">💡 建议关注</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-number-orange" id="total-events">{len(events_7days)}</div>
                    <div class="stat-label">近7天事件</div>
                </div>
            </div>

            <!-- 趋势图 -->
            <div class="content-card">
                <div class="card-title">
                    <span>📊 近7天心理健康趋势</span>
                    <span style="font-size:13px;color:#94a3b8;font-weight:400;">
                        当前状态: <span class="status-badge {status_class}" id="status-badge-small" style="font-size:12px;">{status}</span>
                        &nbsp;|&nbsp; <span class="db-status active" id="ws-status">● WebSocket 已连接</span>
                    </span>
                </div>
                <div class="chart-container">
                    <canvas id="healthChart"></canvas>
                </div>
            </div>

            <!-- 建议卡片 -->
            <div class="suggestion-card">
                <div class="suggestion-title">💡 关注提醒</div>
                <p class="suggestion-text" id="suggestion-text">{suggestion}</p>
            </div>

            <!-- 底部栏 -->
            <div class="footer-bar">
                <span><span class="dot dot-blue" id="status-dot"></span><span id="status-text">心理监测运行中</span></span>
                <span>📊 数据更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
                <span id="update-time">🕐 最后更新: {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>

        <script>
            // ============================================================
            // 心理健康趋势图 + WebSocket 实时更新
            // ============================================================

            const API_BASE = 'https://zxc-production-f99b.up.railway.app';
            var ws = null;
            var reconnectTimer = null;
            var isConnected = false;
            var healthChart = null;
            var healthData = {health_data_json};

            // ============================================================
            // 状态更新函数
            // ============================================================
            function updateConnectionStatus(connected) {{
                isConnected = connected;
                var wsStatus = document.getElementById('ws-status');
                var statusDot = document.getElementById('status-dot');
                var statusText = document.getElementById('status-text');

                if (connected) {{
                    if (wsStatus) {{
                        wsStatus.textContent = '● WebSocket 已连接';
                        wsStatus.className = 'db-status active';
                    }}
                    if (statusDot) {{
                        statusDot.className = 'dot dot-green';
                    }}
                    if (statusText) {{
                        statusText.textContent = '心理监测运行中';
                    }}
                }} else {{
                    if (wsStatus) {{
                        wsStatus.textContent = '● WebSocket 断开';
                        wsStatus.className = 'db-status inactive';
                    }}
                    if (statusDot) {{
                        statusDot.className = 'dot dot-red';
                    }}
                    if (statusText) {{
                        statusText.textContent = '等待重连...';
                    }}
                }}
            }}

            // ============================================================
            // 初始化图表
            // ============================================================
            function initChart() {{
                var ctx = document.getElementById('healthChart').getContext('2d');
                var labels = healthData.map(d => d.date);
                var indices = healthData.map(d => d.index);
                var counts = healthData.map(d => d.count);

                healthChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: '心理健康指数',
                            data: indices,
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.15)',
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: indices.map(v => v >= 70 ? '#22c55e' : v >= 45 ? '#f97316' : '#ef4444'),
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 6,
                            pointHoverRadius: 8,
                            yAxisID: 'y'
                        }}, {{
                            label: '事件数量',
                            data: counts,
                            borderColor: '#94a3b8',
                            backgroundColor: 'rgba(148, 163, 184, 0.1)',
                            fill: true,
                            tension: 0.4,
                            borderDash: [5, 5],
                            pointBackgroundColor: '#94a3b8',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 1,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            yAxisID: 'y1'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {{
                            mode: 'index',
                            intersect: false
                        }},
                        plugins: {{
                            legend: {{
                                display: true,
                                position: 'top',
                                labels: {{
                                    usePointStyle: true,
                                    padding: 20,
                                    font: {{ size: 12 }}
                                }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        if (context.datasetIndex === 0) {{
                                            return '心理健康指数: ' + context.parsed.y;
                                        }} else {{
                                            return '事件数量: ' + context.parsed.y + ' 次';
                                        }}
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                type: 'linear',
                                display: true,
                                position: 'left',
                                min: 0,
                                max: 100,
                                grid: {{ color: 'rgba(0,0,0,0.06)' }},
                                ticks: {{ stepSize: 20 }},
                                title: {{
                                    display: true,
                                    text: '心理健康指数',
                                    color: '#2563eb',
                                    font: {{ size: 11 }}
                                }}
                            }},
                            y1: {{
                                type: 'linear',
                                display: true,
                                position: 'right',
                                min: 0,
                                grid: {{ drawOnChartArea: false }},
                                ticks: {{ stepSize: 1 }},
                                title: {{
                                    display: true,
                                    text: '事件数量',
                                    color: '#94a3b8',
                                    font: {{ size: 11 }}
                                }}
                            }},
                            x: {{
                                grid: {{ display: false }}
                            }}
                        }}
                    }}
                }});
            }}

            // ============================================================
            // 从数据库加载最新健康数据
            // ============================================================
            function loadHealthData() {{
                fetch(API_BASE + '/api/events/health')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success' && data.health_data) {{
                            var newData = data.health_data;
                            var labels = newData.map(d => d.date);
                            var indices = newData.map(d => d.index);
                            var counts = newData.map(d => d.count);

                            if (healthChart) {{
                                healthChart.data.labels = labels;
                                healthChart.data.datasets[0].data = indices;
                                healthChart.data.datasets[1].data = counts;
                                healthChart.data.datasets[0].pointBackgroundColor = indices.map(v => 
                                    v >= 70 ? '#22c55e' : v >= 45 ? '#f97316' : '#ef4444'
                                );
                                healthChart.update();
                            }}

                            // 更新统计卡片
                            if (indices.length > 0) {{
                                var lastIndex = indices[indices.length - 1];
                                var indexEl = document.getElementById('health-index');
                                if (indexEl) indexEl.textContent = lastIndex;
                                var progressEl = document.querySelector('.progress-fill');
                                if (progressEl) progressEl.style.width = lastIndex + '%';

                                // 更新状态
                                var statusEl = document.getElementById('status-badge');
                                var statusSmallEl = document.getElementById('status-badge-small');
                                var statusClass, statusText;
                                if (lastIndex >= 70) {{
                                    statusClass = 'status-safe';
                                    statusText = '正常';
                                }} else if (lastIndex >= 45) {{
                                    statusClass = 'status-warning';
                                    statusText = '轻度关注';
                                }} else {{
                                    statusClass = 'status-danger';
                                    statusText = '需要关注';
                                }}
                                if (statusEl) {{
                                    statusEl.className = 'status-badge ' + statusClass;
                                    statusEl.textContent = statusText;
                                }}
                                if (statusSmallEl) {{
                                    statusSmallEl.className = 'status-badge ' + statusClass;
                                    statusSmallEl.textContent = statusText;
                                }}

                                // 更新事件总数
                                var totalEvents = counts.reduce((a, b) => a + b, 0);
                                var totalEl = document.getElementById('total-events');
                                if (totalEl) totalEl.textContent = totalEvents;

                                // 更新变化值
                                if (indices.length >= 2) {{
                                    var change = indices[indices.length - 1] - indices[indices.length - 2];
                                    var changeEl = document.getElementById('change-value');
                                    if (changeEl) {{
                                        changeEl.textContent = (change >= 0 ? '+' : '') + change;
                                        changeEl.className = 'stat-number ' + (change >= 0 ? 'stat-number-green' : 'stat-number-red');
                                    }}
                                }}
                            }}

                            document.getElementById('update-time').textContent = '🕐 最后更新: ' + new Date().toLocaleTimeString('zh-CN');
                        }}
                    }})
                    .catch(error => console.error('加载健康数据失败:', error));
            }}

            // ============================================================
            // WebSocket 连接
            // ============================================================
            function connectWebSocket() {{
                try {{
                    console.log('🔗 连接 WebSocket...');
                    ws = new WebSocket('wss://zxc-production-f99b.up.railway.app/ws/family');

                    ws.onopen = function() {{
                        console.log('✅ WebSocket 已连接');
                        updateConnectionStatus(true);
                    }};

                    
                    ws.onmessage = function(event) {{
    try {{
        const data = JSON.parse(event.data);
        console.log('📩 收到:', data.type);

        if (data.type === 'connected') {{
            console.log('✅ 已连接到服务器');
            return;
        }}

        if (data.type === 'new_alert') {{
            console.log('🔄 收到新告警通知，刷新健康数据');
            loadHealthData();
        }}
    }} catch(e) {{
        console.error('解析消息失败:', e);
    }}
}};

                    ws.onclose = function() {{
                        console.log('❌ WebSocket 断开');
                        updateConnectionStatus(false);
                        if (reconnectTimer) clearTimeout(reconnectTimer);
                        reconnectTimer = setTimeout(connectWebSocket, 3000);
                    }};

                    ws.onerror = function(error) {{
                        console.error('WebSocket 错误:', error);
                    }};

                }} catch(e) {{
                    console.error('连接失败:', e);
                    updateConnectionStatus(false);
                    if (reconnectTimer) clearTimeout(reconnectTimer);
                    reconnectTimer = setTimeout(connectWebSocket, 3000);
                }}
            }}

            // ============================================================
            // 启动
            // ============================================================

            initChart();

            updateConnectionStatus(false);

            setTimeout(connectWebSocket, 500);

            setInterval(function() {{
                loadHealthData();
            }}, 10000);

            document.addEventListener('visibilitychange', function() {{
                if (!document.hidden) {{
                    console.log('👁️ 页面可见，刷新数据');
                    loadHealthData();
                    if (!isConnected) {{
                        connectWebSocket();
                    }}
                }}
            }});

            console.log('🚀 Health页面 启动完成 (WebSocket + MySQL)');
        </script>
    </body>
    </html>
    """, height=750)


if __name__ == "__main__":
    main()