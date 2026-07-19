# pages/history.py
import streamlit as st
import json
from datetime import datetime, timedelta
from utils.auth import require_auth, get_current_user
from utils.db import get_events_last_days, get_all_events


@require_auth
def main():
    user = get_current_user()

    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; padding: 16px 0 12px 0; border-bottom: 3px solid #f97316; margin-bottom: 16px;">
        <span style="font-size: 28px;">📚</span>
        <h1 style="font-size: 26px; font-weight: 700; color: #1e293b; margin: 0;">历史记录</h1>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 【关键】从 MySQL 加载历史数据（只保留近15天）
    # ============================================================
    events = get_events_last_days(15)

    # 转换 datetime
    for e in events:
        if isinstance(e.get('timestamp'), datetime):
            e['timestamp'] = e['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(e.get('created_at'), datetime):
            e['created_at'] = e['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    # ============================================================
    # 【修改】筛选功能 - 使用下拉选择
    # ============================================================
    # 获取所有事件类型和等级
    all_types = list(set([e.get('alert_type', '未知') for e in events]))
    all_levels = list(set([e.get('level', '低') for e in events]))

    # 筛选控件布局（3列，去掉重置按钮）
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        # 日期范围筛选
        date_option = st.selectbox(
            "📅 时间范围",
            ["今天", "最近3天", "最近7天", "最近15天", "全部"],
            index=3
        )

    with col2:
        # 事件类型筛选 - 下拉选择
        type_options = ["全部"] + sorted(all_types)
        selected_type = st.selectbox(
            "📋 事件类型",
            options=type_options,
            index=0
        )

    with col3:
        # 风险等级筛选 - 下拉选择
        level_options = ["全部"] + sorted(all_levels, key=lambda x: {'高': 0, '中': 1, '低': 2}.get(x, 3))
        selected_level = st.selectbox(
            "⚠️ 风险等级",
            options=level_options,
            index=0
        )

    # ============================================================
    # 应用筛选
    # ============================================================
    filtered_events = events.copy()

    # 日期筛选
    today_str = datetime.now().strftime('%Y-%m-%d')
    if date_option == "今天":
        filtered_events = [e for e in filtered_events if e.get('timestamp', '')[:10] == today_str]
    elif date_option == "最近3天":
        cutoff = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        filtered_events = [e for e in filtered_events if e.get('timestamp', '')[:10] >= cutoff]
    elif date_option == "最近7天":
        cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        filtered_events = [e for e in filtered_events if e.get('timestamp', '')[:10] >= cutoff]
    elif date_option == "最近15天":
        cutoff = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        filtered_events = [e for e in filtered_events if e.get('timestamp', '')[:10] >= cutoff]
    # "全部" 不过滤（但数据本身只有15天）

    # 类型筛选
    if selected_type != "全部":
        filtered_events = [e for e in filtered_events if e.get('alert_type', '未知') == selected_type]

    # 等级筛选
    if selected_level != "全部":
        filtered_events = [e for e in filtered_events if e.get('level', '低') == selected_level]

    # 统计
    today_events = [e for e in filtered_events if e.get('timestamp', '')[:10] == today_str]
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    week_events = [e for e in filtered_events if e.get('timestamp', '')[:10] >= week_ago]
    month_events = filtered_events

    # 将事件数据转为 JSON 传递给前端
    events_json = json.dumps(filtered_events, default=str, ensure_ascii=False)

    st.components.v1.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
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
                grid-template-columns: repeat(3, 1fr);
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
                justify-content: space-between;
                align-items: center;
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

            .footer-bar {{
                display: flex; justify-content: space-between; padding: 10px 18px;
                background: white; border-radius: 10px; margin-top: 15px;
                font-size: 13px; color: #64748b; border: 1px solid #e5e7eb;
                flex-wrap: wrap; gap: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }}
            .footer-bar .dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
            .dot-blue {{ background: #3b82f6; }}

            .empty-state {{
                text-align: center; padding: 40px 20px; color: #94a3b8;
            }}
            .empty-state .empty-icon {{ font-size: 48px; margin-bottom: 12px; }}
            .empty-state .empty-title {{ font-size: 18px; font-weight: 600; color: #475569; margin-bottom: 4px; }}
            .empty-state .empty-desc {{ font-size: 14px; color: #94a3b8; }}

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

            @media screen and (max-width: 768px) {{
                .stats-row {{ grid-template-columns: 1fr; gap: 10px; }}
                .event-time {{ min-width: 80px; font-size: 11px; }}
                .app-container {{ padding: 10px; }}
                .pagination-btn {{ padding: 3px 8px; font-size: 11px; }}
            }}
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- 统计卡片行 -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-number stat-number-blue">{len(today_events)}</div>
                    <div class="stat-label">今日事件</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-number-blue">{len(week_events)}</div>
                    <div class="stat-label">本周事件</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-number-blue">{len(month_events)}</div>
                    <div class="stat-label">筛选结果</div>
                </div>
            </div>

            <!-- 事件列表 -->
            <div class="content-card">
                <div class="card-title">
                    <span>📋 事件记录</span>
                    <span style="font-size:13px;color:#94a3b8;">共 <span id="total-count">{len(filtered_events)}</span> 条</span>
                </div>
                <div class="event-list-container" id="events-list-wrapper">
                    <div id="events-list"></div>
                </div>
                <div class="pagination-container" id="pagination-container"></div>
            </div>

            <!-- 底部栏 -->
            <div class="footer-bar">
                <span><span class="dot dot-blue"></span>数据已同步</span>
                <span>筛选结果: {len(filtered_events)} 条</span>
                <span id="update-time">🕐 最后更新: {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>

        <script>
            // ============================================================
            // 历史记录 - 分页
            // ============================================================

            var allEvents = {events_json};
            var currentPage = 1;
            var pageSize = 15;
            var totalPages = 1;

            console.log('📊 加载事件数:', allEvents.length);

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

            function renderEvents() {{
                var container = document.getElementById('events-list');
                var paginationContainer = document.getElementById('pagination-container');
                if (!container) return;

                var total = allEvents.length;

                if (total === 0) {{
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">📭</div>
                            <div class="empty-title">暂无匹配的事件</div>
                            <div class="empty-desc">请尝试调整筛选条件</div>
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

                document.getElementById('total-count').textContent = total;
                buildPagination(total);
            }}

            function buildPagination(total) {{
                var container = document.getElementById('pagination-container');
                if (!container) return;

                var html = '';

                html += `
                    <select class="page-size-select" onchange="changePageSize(this.value)">
                        <option value="10" ${{pageSize === 10 ? 'selected' : ''}}>10条/页</option>
                        <option value="15" ${{pageSize === 15 ? 'selected' : ''}}>15条/页</option>
                        <option value="20" ${{pageSize === 20 ? 'selected' : ''}}>20条/页</option>
                        <option value="50" ${{pageSize === 50 ? 'selected' : ''}}>50条/页</option>
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

            renderEvents();
            console.log('🚀 History页面 启动完成（分页 + 筛选）');
        </script>
    </body>
    </html>
    """, height=800)


if __name__ == "__main__":
    main()