# pages/risk.py
import streamlit as st
import json
from datetime import datetime, timedelta
from utils.auth import require_auth, get_current_user
from utils.db import get_today_events, get_event_stats
import random


@require_auth
def main():
    user = get_current_user()

    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; padding: 16px 0 12px 0; border-bottom: 3px solid #f97316; margin-bottom: 16px;">
        <span style="font-size: 28px;">⚠️</span>
        <h1 style="font-size: 26px; font-weight: 700; color: #1e293b; margin: 0;">实时风险监控</h1>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 【关键】从 Railway 后端 API 加载今天的数据
    # ============================================================
    events_raw = get_today_events()
    stats = get_event_stats()

    # ============================================================
    # 【修复】将 datetime 对象转换为字符串
    # ============================================================
    events = []
    for e in events_raw:
        event_copy = dict(e)
        if isinstance(event_copy.get('timestamp'), datetime):
            event_copy['timestamp'] = event_copy['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(event_copy.get('created_at'), datetime):
            event_copy['created_at'] = event_copy['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        events.append(event_copy)

    # 将事件数据转换为 JSON 传递给前端
    events_json = json.dumps(events, default=str, ensure_ascii=False)

    # ============================================================
    # 【核心】生成当天小时级别的趋势数据
    # ============================================================
    hour_count = {}
    for e in events:
        timestamp = e.get('timestamp', '')
        if timestamp:
            try:
                if isinstance(timestamp, str) and len(timestamp) >= 13:
                    hour = timestamp[11:13]
                    hour_key = f"{int(hour):02d}:00"
                    hour_count[hour_key] = hour_count.get(hour_key, 0) + 1
            except:
                pass

    today_trend = []
    current_hour = datetime.now().hour
    for h in range(24):
        hour_key = f"{h:02d}:00"
        count = hour_count.get(hour_key, 0)
        if count > 0:
            score = min(100, count * 10 + random.randint(-5, 15))
            score = max(0, score)
        else:
            base_score = max(0, min(30, (h - 6) * 2))
            score = base_score + random.randint(-5, 10)
            score = max(0, min(100, score))

        today_trend.append({
            'hour': hour_key,
            'count': count,
            'score': score,
            'is_past': h <= current_hour
        })

    # 构建类型统计 HTML
    type_stats_html = ''
    if events:
        type_count = {}
        for e in events:
            alert_type = e.get('alert_type', '其他')
            type_count[alert_type] = type_count.get(alert_type, 0) + 1

        type_map = {
            '跌倒告警': {'type_class': 'fall', 'label': '🔴 跌倒'},
            '人形检测': {'type_class': 'person', 'label': '👤 人形'},
            '移动侦测': {'type_class': 'move', 'label': '🚶 移动'},
            '步态异常': {'type_class': 'gait', 'label': '🦶 步态'},
            '长时间静坐': {'type_class': 'sit', 'label': '🪑 久坐'},
            '夜间离床': {'type_class': 'night', 'label': '🌙 离床'},
        }

        for alert_type, count in type_count.items():
            info = type_map.get(alert_type, {'type_class': 'other', 'label': alert_type})
            type_stats_html += f'<span class="type-tag type-tag-{info["type_class"]}">{info["label"]}: {count}次</span>'
    else:
        type_stats_html = '<span style="color:#94a3b8;">暂无数据</span>'

    # 计算综合风险评分
    today_count = len(events)
    if today_count > 0:
        risk_score = min(100, today_count * 8 + random.randint(-5, 10))
        risk_score = max(0, risk_score)
    else:
        risk_score = random.randint(10, 30)

    risk_level = '高' if risk_score > 70 else '中' if risk_score > 40 else '低'

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
                display: inline-block; padding: 3px 12px; border-radius: 20px;
                font-size: 12px; font-weight: 600; white-space: nowrap;
            }}
            .status-danger {{ background: #fee2e2; color: #991b1b; }}
            .status-warning {{ background: #fef3c7; color: #92400e; }}
            .status-safe {{ background: #dcfce7; color: #166534; }}
            .status-info {{ background: #dbeafe; color: #1e40af; }}
            .status-online {{ background: #dbeafe; color: #2563eb; }}
            .status-offline {{ background: #fee2e2; color: #991b1b; }}

            .event-item {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #f1f5f9;
                gap: 8px;
                flex-wrap: wrap;
            }}
            .event-item:last-child {{ border-bottom: none; }}
            .event-time {{ 
                color: #64748b; 
                font-size: 13px; 
                min-width: 120px; 
                white-space: nowrap; 
                font-family: 'Courier New', monospace;
                font-weight: 500;
            }}
            .event-desc {{ 
                flex: 1; 
                margin: 0 8px; 
                font-size: 14px; 
                color: #1e293b; 
                min-width: 80px;
                font-weight: 500;
            }}
            .event-level {{
                min-width: 60px;
                text-align: right;
            }}

            .type-tag {{
                display: inline-block; padding: 2px 10px; border-radius: 12px;
                font-size: 12px; font-weight: 500; margin: 2px 4px;
            }}
            .type-tag-fall {{ background: #fee2e2; color: #991b1b; }}
            .type-tag-person {{ background: #dbeafe; color: #1e40af; }}
            .type-tag-move {{ background: #fef3c7; color: #92400e; }}
            .type-tag-gait {{ background: #fce4ec; color: #c62828; }}
            .type-tag-sit {{ background: #e0f7fa; color: #00695c; }}
            .type-tag-night {{ background: #f3e5f5; color: #6a1b9a; }}
            .type-tag-other {{ background: #f1f5f9; color: #64748b; }}

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
            .dot-green {{ background: #22c55e; }}
            .dot-red {{ background: #ef4444; }}

            .two-col {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 16px;
                margin-bottom: 15px;
            }}

            .empty-state {{
                text-align: center; padding: 40px 20px; color: #94a3b8;
            }}
            .empty-state .empty-icon {{ font-size: 48px; margin-bottom: 12px; }}
            .empty-state .empty-title {{ font-size: 18px; font-weight: 600; color: #475569; margin-bottom: 4px; }}
            .empty-state .empty-desc {{ font-size: 14px; color: #94a3b8; }}

            .db-status {{
                font-size: 12px;
                padding: 4px 12px;
                border-radius: 20px;
            }}
            .db-status.active {{ background: #dcfce7; color: #166534; }}
            .db-status.inactive {{ background: #fee2e2; color: #991b1b; }}
            .db-status.waiting {{ background: #fef3c7; color: #92400e; }}

            .pagination-container {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid #f1f5f9;
                flex-wrap: wrap;
            }}
            .pagination-btn {{
                background: white;
                border: 1px solid #e5e7eb;
                color: #475569;
                padding: 4px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.3s ease;
                min-width: 32px;
                text-align: center;
            }}
            .pagination-btn:hover {{
                background: #f1f5f9;
                border-color: #94a3b8;
            }}
            .pagination-btn.active {{
                background: #2563eb;
                color: white;
                border-color: #2563eb;
            }}
            .pagination-btn:disabled {{
                opacity: 0.4;
                cursor: not-allowed;
            }}
            .pagination-info {{
                color: #94a3b8;
                font-size: 13px;
                padding: 0 8px;
            }}
            .page-size-select {{
                padding: 3px 6px;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                font-size: 12px;
                background: white;
                color: #475569;
                cursor: pointer;
            }}
            .page-size-select:focus {{
                outline: none;
                border-color: #2563eb;
            }}

            .event-list-container {{
                max-height: 450px;
                overflow-y: auto;
            }}
            .event-list-container::-webkit-scrollbar {{
                width: 4px;
            }}
            .event-list-container::-webkit-scrollbar-track {{
                background: #f1f5f9;
                border-radius: 2px;
            }}
            .event-list-container::-webkit-scrollbar-thumb {{
                background: #94a3b8;
                border-radius: 2px;
            }}

            .camera-placeholder {{
                background: linear-gradient(135deg, #0f1629 0%, #1a2332 100%);
                border-radius: 10px;
                height: 380px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #64748b;
                font-size: 16px;
                border: 1px solid #334155;
                min-height: 200px;
                flex-direction: column;
                gap: 10px;
            }}
            .camera-placeholder .icon {{ font-size: 64px; }}
            .camera-placeholder .text {{ color: #94a3b8; }}
            .camera-placeholder .sub {{ font-size: 12px; color: #64748b; }}

            .chart-container {{
                width: 100%;
                height: 220px;
                position: relative;
            }}
            .chart-container canvas {{
                width: 100% !important;
                height: 100% !important;
            }}

            .chart-legend {{
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
                align-items: center;
                padding: 8px 0;
                font-size: 13px;
                color: #64748b;
            }}
            .chart-legend .item {{
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .chart-legend .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
            .chart-legend .dot.orange {{ background: #f97316; }}
            .chart-legend .dot.blue {{ background: #2563eb; }}

            @media screen and (max-width: 768px) {{
                .stats-row {{ grid-template-columns: 1fr 1fr; gap: 10px; }}
                .two-col {{ grid-template-columns: 1fr; }}
                .event-time {{ min-width: 80px; font-size: 11px; }}
                .event-desc {{ font-size: 12px; }}
                .pagination-container {{ gap: 4px; }}
                .pagination-btn {{ padding: 3px 8px; font-size: 11px; }}
                .app-container {{ padding: 10px; }}
                .camera-placeholder {{ height: 250px; }}
                .chart-container {{ height: 160px; }}
            }}
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- 统计卡片行 -->
            <div class="stats-row" id="stats-row">
                <div class="stat-card">
                    <div class="stat-number stat-number-green" id="status-text">🟢 在线</div>
                    <div class="stat-label">当前状态</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-number-{'red' if risk_score > 70 else 'orange' if risk_score > 40 else 'blue'}" id="risk-score">{risk_score}</div>
                    <div class="stat-label">综合风险评分</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-number-orange" id="today-events">{len(events)}</div>
                    <div class="stat-label">今日事件</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-number-blue">30</div>
                    <div class="stat-label">帧率 (FPS)</div>
                </div>
            </div>

            <!-- 告警类型统计 -->
            <div class="content-card" id="type-stats">
                <div class="card-title">📊 告警类型统计</div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;padding:4px 0;">
                    {type_stats_html}
                </div>
            </div>

            <!-- 两列布局 -->
            <div class="two-col">
                <div class="content-card">
                    <div class="card-title">
                        <span>📹 实时监控</span>
                        <span class="status-badge status-online" id="camera-status">● 在线</span>
                    </div>
                    <div class="camera-placeholder">
                        <div class="icon">📷</div>
                        <div class="text">摄像头画面加载中...</div>
                        <div class="sub">骨骼检测运行中</div>
                    </div>
                </div>

                <div class="content-card" id="events-container">
                    <div class="card-title">
                        <span>⚡ 最近事件</span>
                        <span class="db-status active" id="db-status">● 数据库已连接</span>
                    </div>
                    <div class="event-list-container" id="events-list-wrapper">
                        <div id="events-list"></div>
                    </div>
                    <div class="pagination-container" id="pagination-container"></div>
                </div>
            </div>

            <!-- 当天风险趋势 -->
            <div class="content-card">
                <div class="card-title">
                    <span>📊 今日风险趋势 </span>
                    <span style="font-size:13px;color:#94a3b8;font-weight:400;">
                        风险等级: <span style="color:{'#ef4444' if risk_level == '高' else '#f97316' if risk_level == '中' else '#22c55e'};font-weight:600;">{risk_level}</span>
                        &nbsp;|&nbsp; 当前事件: <span style="font-weight:600;">{len(events)}</span>
                    </span>
                </div>
                <div class="chart-container">
                    <canvas id="riskTrendChart"></canvas>
                </div>
                <div class="chart-legend">
                    <span class="item"><span class="dot orange"></span> 风险评分</span>
                    <span class="item"><span class="dot blue"></span> 事件数量</span>
                    <span class="item">📌 当前时间: <span id="current-time-label" style="font-weight:600;color:#1e293b;">--:--</span></span>
                </div>
            </div>

            <!-- 底部栏 -->
            <div class="footer-bar">
                <span><span class="dot dot-green" id="status-dot"></span><span id="status-text-footer">系统运行正常</span></span>
                <span id="device-status">📷 在线  ⌚ 在线  🎤 在线  💡 在线</span>
                <span id="update-time">🕐 最后更新: --:--:--</span>
            </div>
        </div>

        <script>
            // ============================================================
            // WebSocket + 分页 + 状态管理
            // ============================================================

            const API_BASE = 'https://zxc-production-f99b.up.railway.app';
            var ws = null;
            var reconnectTimer = null;
            var isConnected = false;
            var allEvents = [];
            var currentPage = 1;
            var pageSize = 10;
            var totalPages = 1;
            var trendChart = null;
            var currentHourData = {json.dumps(today_trend)};

            // 初始数据
            var initialEvents = {events_json};
            console.log('📊 从数据库加载初始事件数:', initialEvents.length);
            allEvents = initialEvents;

            // ============================================================
            // 更新本地时间（显示用户浏览器时间）
            // ============================================================
            function updateLocalTime() {{
                var now = new Date();
                var h = String(now.getHours()).padStart(2, '0');
                var m = String(now.getMinutes()).padStart(2, '0');
                var s = String(now.getSeconds()).padStart(2, '0');

                var timeLabel = document.getElementById('current-time-label');
                if (timeLabel) {{
                    timeLabel.textContent = h + ':' + m;
                }}

                var updateTimeEl = document.getElementById('update-time');
                if (updateTimeEl) {{
                    updateTimeEl.textContent = '🕐 最后更新: ' + h + ':' + m + ':' + s;
                }}
            }}

            // 立即更新
            updateLocalTime();
            // 每10秒更新一次
            setInterval(updateLocalTime, 10000);

            // ============================================================
            // 状态更新函数
            // ============================================================
            function updateConnectionStatus(connected) {{
                isConnected = connected;

                var statusText = document.getElementById('status-text');
                var statusDot = document.getElementById('status-dot');
                var statusFooter = document.getElementById('status-text-footer');
                var cameraStatus = document.getElementById('camera-status');
                var dbStatus = document.getElementById('db-status');

                if (connected) {{
                    if (statusText) {{
                        statusText.textContent = '🟢 在线';
                        statusText.className = 'stat-number stat-number-green';
                    }}
                    if (statusDot) {{
                        statusDot.className = 'dot dot-green';
                    }}
                    if (statusFooter) {{
                        statusFooter.textContent = '系统运行正常';
                    }}
                    if (cameraStatus) {{
                        cameraStatus.textContent = '● 在线';
                        cameraStatus.className = 'status-badge status-online';
                    }}
                    if (dbStatus) {{
                        dbStatus.textContent = '● WebSocket 已连接';
                        dbStatus.className = 'db-status active';
                    }}
                }} else {{
                    if (statusText) {{
                        statusText.textContent = '🔴 离线';
                        statusText.className = 'stat-number stat-number-red';
                    }}
                    if (statusDot) {{
                        statusDot.className = 'dot dot-red';
                    }}
                    if (statusFooter) {{
                        statusFooter.textContent = '系统离线，等待重连...';
                    }}
                    if (cameraStatus) {{
                        cameraStatus.textContent = '● 离线';
                        cameraStatus.className = 'status-badge status-offline';
                    }}
                    if (dbStatus) {{
                        dbStatus.textContent = '● WebSocket 断开';
                        dbStatus.className = 'db-status inactive';
                    }}
                }}
            }}

            // ============================================================
            // 格式化时间
            // ============================================================
            function formatTime(timestamp) {{
                if (!timestamp) return '';
                if (timestamp.length >= 16) {{
                    var parts = timestamp.split(' ');
                    var datePart = parts[0] || '';
                    var timePart = parts[1] || '';
                    var dateParts = datePart.split('-');
                    var month = dateParts[1] || '';
                    var day = dateParts[2] || '';
                    return month + '-' + day + ' ' + timePart;
                }}
                return timestamp;
            }}

            // ============================================================
            // 初始化趋势图
            // ============================================================
            function initChart(data) {{
                var ctx = document.getElementById('riskTrendChart').getContext('2d');
                var labels = data.map(d => d.hour);
                var scores = data.map(d => d.score);
                var counts = data.map(d => d.count);

                trendChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: '风险评分',
                            data: scores,
                            borderColor: '#f97316',
                            backgroundColor: 'rgba(249, 115, 22, 0.15)',
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: scores.map(s => s > 70 ? '#ef4444' : s > 40 ? '#f97316' : '#22c55e'),
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            segment: {{
                                borderDash: function(context) {{
                                    var index = context.p0DataIndex;
                                    return data[index] && !data[index].is_past ? [5, 5] : [];
                                }}
                            }}
                        }}, {{
                            label: '事件数量',
                            data: counts,
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            fill: true,
                            tension: 0.4,
                            borderDash: [5, 5],
                            pointBackgroundColor: '#2563eb',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            yAxisID: 'y1',
                            segment: {{
                                borderDash: function(context) {{
                                    var index = context.p0DataIndex;
                                    return data[index] && !data[index].is_past ? [5, 5] : [];
                                }}
                            }}
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {{ mode: 'index', intersect: false }},
                        plugins: {{
                            legend: {{
                                display: true,
                                position: 'top',
                                labels: {{ usePointStyle: true, padding: 15, font: {{ size: 12 }} }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        var label = context.dataset.label || '';
                                        var value = context.parsed.y;
                                        if (context.datasetIndex === 0) {{
                                            return label + ': ' + value;
                                        }} else {{
                                            return label + ': ' + value + ' 次';
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
                                title: {{ display: true, text: '风险评分', color: '#f97316', font: {{ size: 11 }} }}
                            }},
                            y1: {{
                                type: 'linear',
                                display: true,
                                position: 'right',
                                min: 0,
                                grid: {{ drawOnChartArea: false }},
                                ticks: {{ stepSize: 1 }},
                                title: {{ display: true, text: '事件数量', color: '#2563eb', font: {{ size: 11 }} }}
                            }},
                            x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 0, autoSkip: true, maxTicksLimit: 12 }} }}
                        }}
                    }}
                }});
            }}

            // ============================================================
            // 更新图表
            // ============================================================
            function updateChartWithNewEvent() {{
                if (!trendChart) return;
                var now = new Date();
                var hour = now.getHours();
                var hourKey = String(hour).padStart(2, '0') + ':00';

                var labels = trendChart.data.labels;
                var scores = trendChart.data.datasets[0].data;
                var counts = trendChart.data.datasets[1].data;

                var index = labels.indexOf(hourKey);
                if (index >= 0) {{
                    counts[index] = (counts[index] || 0) + 1;
                    var newScore = Math.min(100, counts[index] * 10 + Math.floor(Math.random() * 10));
                    scores[index] = Math.max(0, newScore);
                    trendChart.data.datasets[0].pointBackgroundColor[index] = newScore > 70 ? '#ef4444' : newScore > 40 ? '#f97316' : '#22c55e';
                }}
                trendChart.update();
            }}

            // ============================================================
            // 渲染事件列表
            // ============================================================
            function renderEvents() {{
                var container = document.getElementById('events-list');
                var paginationContainer = document.getElementById('pagination-container');
                if (!container) return;

                var total = allEvents.length;

                if (total === 0) {{
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">⏳</div>
                            <div class="empty-title">等待数据推送...</div>
                            <div class="empty-desc">WebSocket 连接中，告警将自动保存到数据库</div>
                        </div>
                    `;
                    if (paginationContainer) paginationContainer.innerHTML = '';
                    return;
                }}

                totalPages = Math.ceil(total / pageSize);
                if (currentPage > totalPages) currentPage = totalPages;
                if (currentPage < 1) currentPage = 1;

                var start = (currentPage - 1) * pageSize;
                var end = Math.min(start + pageSize, total);
                var pageEvents = allEvents.slice(start, end);

                var itemsHtml = '';
                pageEvents.forEach(function(e) {{
                    var levelMap = {{'高':'status-danger','中':'status-warning','低':'status-safe'}};
                    var levelClass = levelMap[e.level] || 'status-safe';
                    var time = e.timestamp || '';
                    var timeDisplay = formatTime(time);
                    var icon = e.level === '高' ? '🔴' : e.level === '中' ? '🟡' : '✅';
                    var levelText = e.level || '低风险';
                    itemsHtml += `
                        <div class="event-item">
                            <span class="event-time">${{timeDisplay}}</span>
                            <span class="event-desc"><span>${{icon}}</span> ${{e.alert_type || '未知事件'}}</span>
                            <span class="event-level"><span class="status-badge ${{levelClass}}">${{levelText}}</span></span>
                        </div>
                    `;
                }});

                container.innerHTML = `
                    <div style="margin-bottom:8px;font-size:13px;color:#64748b;">
                        共 ${{total}} 条事件 · 显示第 ${{start+1}}-${{end}} 条
                    </div>
                    ${{itemsHtml}}
                `;

                var statEl = document.getElementById('today-events');
                if (statEl) statEl.textContent = total;

                buildPagination(total);
            }}

            // ============================================================
            // 分页控件
            // ============================================================
            function buildPagination(total) {{
                var container = document.getElementById('pagination-container');
                if (!container) return;

                var html = '';
                html += `
                    <select class="page-size-select" onchange="changePageSize(this.value)">
                        <option value="5" ${{pageSize === 5 ? 'selected' : ''}}>5条/页</option>
                        <option value="10" ${{pageSize === 10 ? 'selected' : ''}}>10条/页</option>
                        <option value="20" ${{pageSize === 20 ? 'selected' : ''}}>20条/页</option>
                        <option value="50" ${{pageSize === 50 ? 'selected' : ''}}>50条/页</option>
                        <option value="100" ${{pageSize === 100 ? 'selected' : ''}}>100条/页</option>
                    </select>
                `;

                if (total <= pageSize) {{
                    html += `<span class="pagination-info">共 ${{total}} 条</span>`;
                    container.innerHTML = html;
                    return;
                }}

                html += `<span class="pagination-info">共 ${{total}} 条</span>`;

                html += `<button class="pagination-btn" onclick="goToPage(${{currentPage - 1}})" ${{currentPage <= 1 ? 'disabled' : ''}}>‹</button>`;

                var maxShow = 5;
                var startPage = Math.max(1, currentPage - Math.floor(maxShow / 2));
                var endPage = Math.min(totalPages, startPage + maxShow - 1);
                if (endPage - startPage < maxShow - 1) {{
                    startPage = Math.max(1, endPage - maxShow + 1);
                }}

                if (startPage > 1) {{
                    html += `<button class="pagination-btn" onclick="goToPage(1)">1</button>`;
                    if (startPage > 2) html += `<span class="pagination-info">...</span>`;
                }}

                for (var i = startPage; i <= endPage; i++) {{
                    html += `<button class="pagination-btn ${{i === currentPage ? 'active' : ''}}" onclick="goToPage(${{i}})">${{i}}</button>`;
                }}

                if (endPage < totalPages) {{
                    if (endPage < totalPages - 1) html += `<span class="pagination-info">...</span>`;
                    html += `<button class="pagination-btn" onclick="goToPage(${{totalPages}})">${{totalPages}}</button>`;
                }}

                html += `<button class="pagination-btn" onclick="goToPage(${{currentPage + 1}})" ${{currentPage >= totalPages ? 'disabled' : ''}}>›</button>`;

                container.innerHTML = html;
            }}

            function goToPage(page) {{
                if (page < 1 || page > totalPages) return;
                currentPage = page;
                renderEvents();
                var wrapper = document.getElementById('events-list-wrapper');
                if (wrapper) wrapper.scrollTop = 0;
            }}

            function changePageSize(size) {{
                pageSize = parseInt(size);
                currentPage = 1;
                renderEvents();
            }}

            window.goToPage = goToPage;
            window.changePageSize = changePageSize;

            function updateEvents(events) {{
                 allEvents = events || [];
    var totalPages = Math.ceil(allEvents.length / pageSize);
    if (currentPage > totalPages) {{
        if (totalPages > 0) {{
            currentPage = totalPages;
        }} else {{
            currentPage = 1;
        }}
    }}
    renderEvents();
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

                            // 连接确认消息，不做特殊处理
                            if (data.type === 'connected') {{
                                console.log('✅ 已连接到服务器');
                                return;
                            }}

                            // ✅ 收到新告警通知 → 只刷新数据，不再上报
                            if (data.type === 'new_alert') {{
                                console.log('🔄 收到新告警通知，刷新数据');
                                loadEventsFromDB();
                                updateChartWithNewEvent();
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
            // 从数据库加载事件
            // ============================================================
            function loadEventsFromDB() {{
                fetch(API_BASE + '/api/events/today')
                .then(response => response.json())
                .then(data => {{
                    if (data.status === 'success') {{
                        console.log('📊 从数据库加载事件，共', data.total, '条');
                        updateEvents(data.events);
                    }}
                }})
                .catch(error => console.error('加载事件失败:', error));
            }}

            // ============================================================
            // 启动
            // ============================================================

            // 初始化图表
            initChart(currentHourData);

            // 加载事件列表
            updateEvents(initialEvents);

            // 初始状态设为未连接（等待 WebSocket 连接）
            updateConnectionStatus(false);

            // 连接 WebSocket
            setTimeout(connectWebSocket, 500);

            // 定时刷新（每5秒）
            setInterval(function() {{
                loadEventsFromDB();
            }}, 5000);

            document.addEventListener('visibilitychange', function() {{
                if (!document.hidden) {{
                    console.log('👁️ 页面可见，刷新数据');
                    loadEventsFromDB();
                    if (!isConnected) {{
                        connectWebSocket();
                    }}
                }}
            }});

            console.log('🚀 Risk页面 启动完成');
        </script>
    </body>
    </html>
    """, height=1350)


if __name__ == "__main__":
    main()