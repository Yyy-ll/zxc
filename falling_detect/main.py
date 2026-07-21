# main.py
import streamlit as st
import base64
import os
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from utils.auth import get_current_user
from pathlib import Path
from utils.database import init_database

# ========== 提供 Service Worker 文件 ==========
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

sw_path = static_dir / "sw.js"
if not sw_path.exists():
    sw_content = '''// static/sw.js ... (保持原有内容)'''
    with open(sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)
    print("✅ sw.js 已创建")

# ========== 页面配置 ==========
st.set_page_config(
    page_title="银龄安居 - 跌倒风险预警系统",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_database()

# ========== 加载用户配置 ==========
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)  # ← 缩进 4 个空格

# ========== 创建认证器 ==========
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# ========== 渲染登录界面 ==========
authenticator.login(location='sidebar')


# ========== 读取图片 ==========
def get_image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


current_dir = Path(__file__).parent
logo_path = current_dir / "图片1.png"
logo_base64 = get_image_base64(str(logo_path)) if logo_path.exists() else None

# ========== 检查登录状态 ==========
auth_status = st.session_state.get('authentication_status')

# 密码错误时显示错误提示
if auth_status is False:
    st.error('❌ 用户名或密码错误，请重新输入')

# ========== 未登录时显示 ==========
if not auth_status:
    st.markdown("""
     <style>
         .main > div {
             display: flex;
             justify-content: center;
             align-items: center;
             min-height: 70vh;
         }
         .block-container {
             max-width: 600px !important;
             padding: 40px 20px !important;
             margin: 0 auto !important;
         }
         .stApp {
             background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 40%, #fef3c7 100%) !important;
         }
         .login-card {
             background: rgba(255, 255, 255, 0.75);
             backdrop-filter: blur(10px);
             -webkit-backdrop-filter: blur(10px);
             border-radius: 24px;
             padding: 40px 30px;
             box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
             border: 1px solid rgba(255, 255, 255, 0.3);
         }
     </style>
     """, unsafe_allow_html=True)

    st.markdown(f"""
     <div style="text-align: center; padding: 20px 0;">
         <div class="login-card">
             <img src="data:image/png;base64,{logo_base64}" 
                  style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #f97316; box-shadow: 0 4px 16px rgba(249, 115, 22, 0.3);">
             <div style="font-size: 42px; color: #f97316; margin: 16px 0 4px 0; font-weight: 700;">银龄安居</div>
             <p style="font-size: 18px; color: #64748b; margin: 0;">跌倒风险预警系统</p>
             <p style="font-size: 16px; color: #475569; margin: 30px 0 0 0;">请登录以访问系统</p>
             <p style="font-size: 14px; color: #94a3b8; margin: 4px 0 0 0;">请在左侧侧边栏输入账号和密码</p>
         </div>
     </div>
     """, unsafe_allow_html=True)

    st.stop()

# ========== 登录成功，显示主内容 ==========

# ========== 获取当前用户信息 ==========
current_user = get_current_user()

# ========== 自定义CSS样式 ==========
st.markdown("""
 <style>
     [data-testid="stSidebarNav"] {
         background: transparent !important;
         padding: 5px 0 !important;
     }
     [data-testid="stSidebarNav"] a {
         font-size: 15px !important;
         padding: 4px 16px !important;
         border-radius: 8px !important;
         margin: 2px 8px !important;
         transition: all 0.3s ease !important;
         color: #475569 !important;
         text-decoration: none !important;
         display: block !important;
     }
     [data-testid="stSidebarNav"] a:hover {
         background-color: #e2e8f0 !important;
         color: #1e293b !important;
     }
     [data-testid="stSidebarNav"] a[aria-current="page"] {
         background: linear-gradient(90deg, #2563eb, #f97316) !important;
         color: white !important;
         font-weight: 500 !important;
         box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
     }
     [data-testid="stSidebarNav"] a svg {
         margin-right: 10px !important;
         color: #64748b !important;
     }
     [data-testid="stSidebarNav"] a[aria-current="page"] svg {
         color: white !important;
     }
     [data-testid="stSidebarNav"] hr {
         border-color: #e5e7eb !important;
         margin: 4px 12px !important;
     }
     [data-testid="stSidebarNav"] .st-emotion-cache-1wivap2 {
         color: #1e293b !important;
         font-weight: 600 !important;
         font-size: 13px !important;
         padding: 4px 16px !important;
         letter-spacing: 0.5px !important;
     }
     section[data-testid="stSidebar"] {
         background: #f8fafc !important;
         padding-top: 10px !important;
         border-right: 1px solid #e5e7eb !important;
         display: flex;
         flex-direction: column !important;
     }
     .sidebar-header {
         text-align: center;
         padding: 8px 0 6px 0;
         border-bottom: 1px solid #e5e7eb !important;
         margin-bottom: 0px;
         flex-shrink: 0;
     }
     .sidebar-header .logo {
         font-size: 48px;
         display: block;
     }
     .sidebar-header h2 {
         color: #f97316;
         margin: 0px 0 0px 0;
         font-size: 18px;
     }
     .sidebar-header p {
         color: #94a3b8;
         font-size: 11px;
         margin: 0;
     }
     [data-testid="stSidebarNav"] {
         flex: 1 !important;
     }
     .sidebar-footer-actions {
         flex-shrink: 0;
         padding: 25px 16px 25px 16px;
         border-top: 1px solid #e5e7eb;
         margin-top: auto;
         display: flex;
         flex-direction: column;
         gap: 12px;
     }
     .sidebar-footer-actions .btn-call {
         display: flex;
         align-items: center;
         justify-content: center;
         gap: 10px;
         padding: 14px 16px;
         border-radius: 10px;
         font-size: 15px;
         font-weight: 600;
         cursor: pointer;
         border: none;
         transition: all 0.3s ease;
         width: 100%;
     }
     .sidebar-footer-actions .btn-call:hover {
         transform: translateY(-2px);
     }
     .sidebar-footer-actions .btn-call-family {
         background: linear-gradient(135deg, #2563eb, #3b82f6);
         color: white;
     }
     .sidebar-footer-actions .btn-call-family:hover {
         box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35);
     }
     .sidebar-footer-actions .btn-call-emergency {
         background: linear-gradient(135deg, #ef4444, #dc2626);
         color: white;
         animation: pulse-ring 2s infinite;
     }
     .sidebar-footer-actions .btn-call-emergency:hover {
         box-shadow: 0 4px 16px rgba(239, 68, 68, 0.4);
     }
     @keyframes pulse-ring {
         0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.3); }
         50% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
     }
     .sidebar-footer-actions .btn-icon {
         font-size: 18px;
     }
     .sidebar-footer-actions .btn-version {
         text-align: center;
         color: #94a3b8;
         font-size: 11px;
         padding-top: 4px;
         user-select: none;
     }
     .main > div {
         padding: 0 !important;
         max-width: 100% !important;
     }
     .block-container {
         padding: 0 !important;
         max-width: 100% !important;
     }
     .stApp {
         background: #f0f4f8;
     }
     .page-header {
         display: flex;
         align-items: center;
         gap: 12px;
         padding: 10px 0 10px 0;
         border-bottom: 3px solid #f97316;
         margin-bottom: 20px;
     }
     .page-header h1 {
         font-size: 26px;
         font-weight: 700;
         color: #1e293b;
         margin: 0;
     }
     .page-header span {
         font-size: 28px;
     }
     .content-card {
         background: white;
         padding: 20px 24px;
         border-radius: 15px;
         box-shadow: 0 2px 12px rgba(37, 99, 235, 0.08);
         margin-bottom: 15px;
         border: 1px solid rgba(37, 99, 235, 0.06);
     }
     .stat-card {
         background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
         padding: 16px 16px;
         border-radius: 12px;
         text-align: center;
         border: 1px solid #e5e7eb;
         transition: all 0.3s ease;
         height: 100%;
         box-shadow: 0 2px 8px rgba(0,0,0,0.04);
     }
     .stat-card:hover {
         transform: translateY(-3px);
         box-shadow: 0 8px 24px rgba(37, 99, 235, 0.12);
         border-color: #3b82f6;
     }
     .stat-number {
         font-size: 28px;
         font-weight: 700;
         color: #1e293b;
     }
     .stat-number-blue {color: #2563eb;}
     .stat-number-orange {color: #f97316;}
     .stat-number-green {color: #16a34a;}
     .stat-label {
         font-size: 13px;
         color: #64748b;
         margin-top: 4px;
     }
     .status-badge {
         display: inline-block;
         padding: 3px 12px;
         border-radius: 20px;
         font-size: 12px;
         font-weight: 600;
     }
     .status-safe {background: #dcfce7; color: #166534;}
     .status-warning {background: #fef3c7; color: #92400e;}
     .status-danger {background: #fee2e2; color: #991b1b;}
     .status-info {background: #dbeafe; color: #1e40af;}
     .status-online {background: #dbeafe; color: #2563eb;}
     .event-item {
         display: flex;
         align-items: center;
         justify-content: space-between;
         padding: 10px 0;
         border-bottom: 1px solid #f1f5f9;
     }
     .event-item:last-child {border-bottom: none;}
     .event-time {
         color: #94a3b8;
         font-size: 13px;
         min-width: 60px;
     }
     .event-desc {
         flex: 1;
         margin: 0 12px;
         font-size: 14px;
         color: #1e293b;
     }
     .event-icon-safe {color: #22c55e;}
     .event-icon-warning {color: #f97316;}
     .event-icon-danger {color: #ef4444;}
     .footer-bar {
         display: flex;
         justify-content: space-between;
         padding: 10px 18px;
         background: white;
         border-radius: 10px;
         margin-top: 15px;
         font-size: 13px;
         color: #64748b;
         border: 1px solid #e5e7eb;
         flex-wrap: wrap;
         gap: 8px;
         box-shadow: 0 2px 8px rgba(0,0,0,0.04);
     }
     .footer-bar .dot {
         display: inline-block;
         width: 8px;
         height: 8px;
         border-radius: 50%;
         margin-right: 6px;
     }
     .dot-green {background: #22c55e;}
     .dot-blue {background: #3b82f6;}
     .dot-orange {background: #f97316;}
     .welcome-container {
         display: flex;
         flex-direction: column;
         align-items: center;
         justify-content: center;
         text-align: center;
         padding: 60px 20px;
         min-height: 500px;
     }
     .welcome-title {
         font-size: 48px;
         font-weight: 700;
         color: #1e293b;
         margin-bottom: 16px;
     }
     .welcome-subtitle {
         font-size: 20px;
         color: #64748b;
         margin-bottom: 30px;
     }
     .welcome-icon {
         font-size: 80px;
         margin-bottom: 20px;
     }
     .welcome-features {
         display: flex;
         gap: 30px;
         flex-wrap: wrap;
         justify-content: center;
         margin-top: 30px;
     }
     .welcome-feature-item {
         background: white;
         padding: 20px 30px;
         border-radius: 12px;
         border: 1px solid #e5e7eb;
         box-shadow: 0 2px 8px rgba(0,0,0,0.04);
         min-width: 150px;
     }
     .welcome-feature-item .icon {
         font-size: 32px;
         display: block;
         margin-bottom: 8px;
     }
     .welcome-feature-item .label {
         font-size: 14px;
         color: #1e293b;
         font-weight: 500;
     }
     .welcome-feature-item .desc {
         font-size: 12px;
         color: #94a3b8;
         margin-top: 4px;
     }
     .nav-hint {
         background: #f1f5f9;
         border-radius: 8px;
         padding: 12px 20px;
         margin-top: 30px;
         color: #475569;
         font-size: 14px;
     }
 </style>
 """, unsafe_allow_html=True)

# ========== 侧边栏自定义内容 ==========
with st.sidebar:
    st.markdown(f"""
     <div class="sidebar-header">
         <span class="logo">
             <img src="data:image/png;base64,{logo_base64}" 
                  style="width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid #f97316; box-shadow: 0 4px 16px rgba(249, 115, 22, 0.3);">
         </span>
         <h2>银龄安居</h2>
         <p>跌倒风险预警系统</p>
         <p style="color: #475569; font-size: 13px; margin-top: 8px;">👋 欢迎，{current_user['name']}</p>
     </div>
     """, unsafe_allow_html=True)

# ========== 使用 st.navigation 控制页面 ==========
page_risk = st.Page("pages/risk.py", title="实时风险", icon="⚠️")
page_health = st.Page("pages/health.py", title="心理健康", icon="❤️")
page_trend = st.Page("pages/trend.py", title="趋势预测", icon="📈")
page_history = st.Page("pages/history.py", title="历史记录", icon="📚")
page_feedback = st.Page("pages/feedback.py", title="反馈", icon="💬")

pg = st.navigation(
    [page_risk, page_health, page_trend, page_history, page_feedback],
    position="sidebar",
    expanded=True
)

# ===== 在st.navigation之后添加底部按钮 =====
st.sidebar.markdown("""
 <div class="sidebar-footer-actions">
     <a href="tel:17737928701" class="btn-call btn-call-family" style="text-decoration:none;display:flex;align-items:center;justify-content:center;gap:10px;padding:14px 16px;border-radius:10px;font-size:15px;font-weight:600;width:100%;background:linear-gradient(135deg,#2563eb,#3b82f6);color:white;border:none;cursor:pointer;transition:all 0.3s ease;">
         <span class="btn-icon">📞</span> 联系老人
     </a>
     <a href="tel:17737928701" class="btn-call btn-call-emergency" style="text-decoration:none;display:flex;align-items:center;justify-content:center;gap:10px;padding:14px 16px;border-radius:10px;font-size:15px;font-weight:600;width:100%;background:linear-gradient(135deg,#ef4444,#dc2626);color:white;border:none;cursor:pointer;transition:all 0.3s ease;animation:pulse-ring 2s infinite;">
         <span class="btn-icon">🆘</span> 紧急求助
     </a>
 </div>
 """, unsafe_allow_html=True)

# ===== 登出按钮 =====
st.sidebar.divider()


# ============================================================
# 登出函数 - 只设置标志
# ============================================================
def logout_user():
    st.session_state._logout = True


# 创建登出按钮
st.sidebar.button(
    "🚪 退出登录",
    use_container_width=True,
    on_click=logout_user
)

# ============================================================
# 在页面底部检查登出状态
# ============================================================
if st.session_state.get('_logout', False):
    st.session_state._logout = False
    # 清除所有 session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # 清除 Cookie 并刷新
    st.components.v1.html("""
    <script>
        // 清除所有 cookie
        document.cookie.split(";").forEach(function(c) {
            var name = c.replace(/^ +/, "").split("=")[0];
            if (name) {
                document.cookie = name + "=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT";
                document.cookie = name + "=;path=/;domain=" + location.hostname + ";expires=Thu, 01 Jan 1970 00:00:00 GMT";
            }
        });
        // 清除认证 cookie
        document.cookie = "yinling_anjia_cookie=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT";
        document.cookie = "yinling_anjia_cookie=;path=/;domain=" + location.hostname + ";expires=Thu, 01 Jan 1970 00:00:00 GMT";

        console.log("✅ 已清除所有 Cookie");
        // 跳转到当前页面
        window.location.href = window.location.origin + window.location.pathname;
    </script>
    """, height=0)

    st.stop()

# ===== 再次确认登录状态 =====
if not st.session_state.get('authentication_status', False):
    st.error("⚠️ 请先登录系统")
    st.stop()

# 运行当前选中的页面
pg.run()