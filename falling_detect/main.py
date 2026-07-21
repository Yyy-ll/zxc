# main.py - 登录/注册 + 主应用
import streamlit as st
import base64
import os
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from utils.database import init_database
from utils.auth import (
    login_user, register_user, is_authenticated,
    get_current_user, get_user_role, get_user_name,
    get_user_phone, get_emergency_contact, logout,
    validate_phone
)

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


# ============================================================
# 登录/注册页面（未登录时显示）
# ============================================================
def login_page():
    # 初始化 session_state 控制显示登录还是注册
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False

    # ========== 未登录时显示（主区域） ==========
    st.markdown("""
     <style>
         .main > div {
             display: flex;
             justify-content: center;
             align-items: center;
             min-height: 70vh;
         }
         .block-container {
             max-width: 700px !important;
             padding: 50px 30px !important;
             margin: 0 auto !important;
         }
         .stApp {
             background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 40%, #fef3c7 100%) !important;
         }
         .login-card {
             background: rgba(255, 255, 255, 0.85);
             backdrop-filter: blur(12px);
             -webkit-backdrop-filter: blur(12px);
             border-radius: 28px;
             padding: 50px 40px;
             box-shadow: 0 12px 48px rgba(0, 0, 0, 0.10);
             border: 1px solid rgba(255, 255, 255, 0.4);
             text-align: center;
         }
         .login-card .logo-img {
             width: 120px;
             height: 120px;
             border-radius: 50%;
             object-fit: cover;
             border: 4px solid #f97316;
             box-shadow: 0 8px 24px rgba(249, 115, 22, 0.25);
         }
         .login-card .app-name {
             font-size: 48px;
             color: #f97316;
             margin: 16px 0 4px 0;
             font-weight: 700;
         }
         .login-card .app-desc {
             font-size: 20px;
             color: #64748b;
             margin: 0;
         }

         /* 登录按钮 - 大号橙色居中 */
         .login-btn > button {
             width: 100% !important;
             background: linear-gradient(135deg, #f97316, #ea580c) !important;
             color: white !important;
             border: none !important;
             border-radius: 12px !important;
             padding: 16px !important;
             font-size: 20px !important;
             font-weight: 700 !important;
             box-shadow: 0 6px 20px rgba(249, 115, 22, 0.4) !important;
             transition: all 0.3s ease !important;
             letter-spacing: 1px !important;
             cursor: pointer !important;
         }
         .login-btn > button:hover {
             background: linear-gradient(135deg, #ea580c, #c2410c) !important;
             box-shadow: 0 8px 28px rgba(249, 115, 22, 0.5) !important;
             transform: translateY(-2px) scale(1.01);
         }
         .login-btn > button:active {
             transform: scale(0.98);
         }

         /* 注册按钮 - 蓝色 */
         .register-btn > button {
             width: 100% !important;
             background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
             color: white !important;
             border: none !important;
             border-radius: 12px !important;
             padding: 16px !important;
             font-size: 20px !important;
             font-weight: 700 !important;
             box-shadow: 0 6px 20px rgba(37, 99, 235, 0.3) !important;
             transition: all 0.3s ease !important;
             letter-spacing: 1px !important;
             cursor: pointer !important;
         }
         .register-btn > button:hover {
             background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
             box-shadow: 0 8px 28px rgba(37, 99, 235, 0.4) !important;
             transform: translateY(-2px) scale(1.01);
         }
         .register-btn > button:active {
             transform: scale(0.98);
         }

         .stTextInput > div > div > input {
             border-radius: 10px !important;
             padding: 12px 16px !important;
             font-size: 15px !important;
             border: 1px solid #e2e8f0 !important;
         }
         .stTextInput > div > div > input:focus {
             border-color: #f97316 !important;
             box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.15) !important;
         }
         .stSelectbox > div > div {
             border-radius: 10px !important;
             padding: 4px 8px !important;
             border: 1px solid #e2e8f0 !important;
         }
         .stSelectbox > div > div > div {
             padding: 8px 12px !important;
         }

         .switch-link {
             text-align: center;
             margin-top: 18px;
             font-size: 15px;
             color: #64748b;
         }
         .switch-link a {
             color: #f97316;
             text-decoration: none;
             font-weight: 600;
             cursor: pointer;
         }
         .switch-link a:hover {
             text-decoration: underline;
         }

         .login-title {
             text-align: center;
             margin-bottom: 24px;
         }
         .login-title h2 {
             color: #1e293b;
             margin: 0;
             font-size: 26px;
             font-weight: 700;
         }
         .login-title p {
             color: #94a3b8;
             margin: 4px 0 0 0;
             font-size: 15px;
         }
         .register-title {
             text-align: center;
             margin-bottom: 24px;
         }
         .register-title h2 {
             color: #1e293b;
             margin: 0;
             font-size: 26px;
             font-weight: 700;
         }
         .register-title p {
             color: #94a3b8;
             margin: 4px 0 0 0;
             font-size: 15px;
         }

         /* 隐藏多余的 stButton */
         .st-emotion-cache-1v0mbdj {
             display: none !important;
         }
         .st-emotion-cache-18ni7ap {
             display: none !important;
         }
     </style>
     """, unsafe_allow_html=True)

    # ========== 主区域显示 Logo 和登录卡片 ==========
    st.markdown(f"""
     <div style="text-align: center; padding: 10px 0;">
         <div class="login-card">
             <img src="data:image/png;base64,{logo_base64}" 
                  class="logo-img">
             <div class="app-name">银龄安居</div>
             <p class="app-desc">跌倒风险预警系统</p>
         </div>
     </div>
     """, unsafe_allow_html=True)

    # ========== 在侧边栏显示登录/注册表单 ==========
    with st.sidebar:
        if st.session_state.show_register:
            # ===== 注册界面 =====
            st.markdown('<div class="register-title"><h2>注册</h2><p>填写信息创建账号</p></div>', unsafe_allow_html=True)
            with st.form("register_form"):
                reg_phone = st.text_input("手机号", placeholder="请输入11位手机号", max_chars=11)
                reg_password = st.text_input("密码", type="password", placeholder="至少6位")
                reg_name = st.text_input("姓名", placeholder="请输入真实姓名")
                reg_role = st.selectbox(
                    "身份",
                    options=["elderly", "family"],
                    format_func=lambda x: "老人" if x == "elderly" else "家属"
                )
                reg_emergency = st.text_input(
                    "紧急联系人",
                    placeholder="请输入紧急联系人手机号",
                    help="老人请填写家属手机号，家属请填写老人手机号"
                )
                # 注册按钮（蓝色）
                st.markdown('<div class="register-btn">', unsafe_allow_html=True)
                reg_submitted = st.form_submit_button("注册", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if reg_submitted:
                    if not all([reg_phone, reg_password, reg_name, reg_emergency]):
                        st.error("请填写完整信息")
                    elif not validate_phone(reg_phone):
                        st.error("手机号必须为11位数字")
                    elif len(reg_password) < 6:
                        st.error("密码长度不少于6位")
                    elif reg_emergency and not validate_phone(reg_emergency):
                        st.error("紧急联系人手机号必须为11位数字")
                    else:
                        success, msg = register_user(reg_phone, reg_password, reg_name, reg_role, reg_emergency)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            # 切换到登录（文字链接）
            st.markdown("""
            <div class="switch-link">
                已有账号？ <a href="#" onclick="document.querySelector('[data-testid=\\'stButton\\'] button').click()">返回登录</a>
            </div>
            """, unsafe_allow_html=True)

            # 隐藏的切换按钮（仅用于JS触发）
            if st.button("切换到登录", key="switch_to_login", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()

        else:
            # ===== 登录界面 =====
            st.markdown('<div class="login-title"><h2>登录</h2><p>输入手机号和密码登录系统</p></div>', unsafe_allow_html=True)
            with st.form("login_form"):
                phone = st.text_input("手机号", placeholder="请输入手机号", max_chars=11)
                password = st.text_input("密码", type="password", placeholder="请输入密码")
                # 登录按钮（橙色大号居中）
                st.markdown('<div class="login-btn">', unsafe_allow_html=True)
                submitted = st.form_submit_button("登录", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if submitted:
                    if not phone or not password:
                        st.error("请填写完整信息")
                    elif not validate_phone(phone):
                        st.error("手机号必须为11位数字")
                    else:
                        success, msg = login_user(phone, password)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            # 切换到注册（文字链接）
            st.markdown("""
            <div class="switch-link">
                没有账号？ <a href="#" onclick="document.querySelector('[data-testid=\\'stButton\\'] button').click()">创建一个</a>
            </div>
            """, unsafe_allow_html=True)

            # 隐藏的切换按钮（仅用于JS触发）
            if st.button("切换到注册", key="switch_to_register", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()


# ============================================================
# 主应用（登录后显示）
# ============================================================
def main_app():
    current_user = get_current_user()
    user_role = get_user_role()
    user_name = get_user_name()
    user_phone = get_user_phone()
    emergency_contact = get_emergency_contact()

    # ============================================================
    # 自定义CSS样式（保留原有全部样式）
    # ============================================================
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
         padding-top: 20px !important;
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

    # ========== 侧边栏 ==========
    with st.sidebar:
        st.markdown(f"""
         <div class="sidebar-header">
             <span class="logo">
                 <img src="data:image/png;base64,{logo_base64}" 
                      style="width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid #f97316; box-shadow: 0 4px 16px rgba(249, 115, 22, 0.3);">
             </span>
             <h2>银龄安居</h2>
             <p>跌倒风险预警系统</p>
             <p style="color: #475569; font-size: 13px; margin-top: 8px;">👋 欢迎，{user_name}</p>
             <p style="color: #94a3b8; font-size: 11px;">{'老人' if user_role == 'elderly' else '家属'} | {user_phone}</p>
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

    # ===== 在st.navigation之后添加底部按钮（根据角色控制） =====
    if user_role == "family":
        call_phone = emergency_contact or "13800138000"
        st.sidebar.markdown(f"""
         <div class="sidebar-footer-actions">
             <a href="tel:{call_phone}" class="btn-call btn-call-family" style="text-decoration:none;display:flex;align-items:center;justify-content:center;gap:10px;padding:14px 16px;border-radius:10px;font-size:15px;font-weight:600;width:100%;background:linear-gradient(135deg,#2563eb,#3b82f6);color:white;border:none;cursor:pointer;transition:all 0.3s ease;">
                 <span class="btn-icon">📞</span> 呼叫老人
             </a>
             <div style="display:flex;align-items:center;justify-content:center;gap:10px;padding:14px 16px;border-radius:10px;font-size:15px;font-weight:600;width:100%;background:#94a3b8;color:white;opacity:0.5;cursor:not-allowed;">
                 <span class="btn-icon">🆘</span> 紧急求助（仅老人可用）
             </div>
         </div>
         """, unsafe_allow_html=True)
    else:
        sos_phone = emergency_contact or "120"
        st.sidebar.markdown(f"""
         <div class="sidebar-footer-actions">
             <div style="display:flex;align-items:center;justify-content:center;gap:10px;padding:14px 16px;border-radius:10px;font-size:15px;font-weight:600;width:100%;background:#94a3b8;color:white;opacity:0.5;cursor:not-allowed;margin-bottom:0px;">
                 <span class="btn-icon">📞</span> 呼叫老人（仅家属可用）
             </div>
             <a href="tel:{sos_phone}" class="btn-call btn-call-emergency" style="text-decoration:none;display:flex;align-items:center;justify-content:center;gap:10px;padding:14px 16px;border-radius:10px;font-size:15px;font-weight:600;width:100%;background:linear-gradient(135deg,#ef4444,#dc2626);color:white;border:none;cursor:pointer;transition:all 0.3s ease;animation:pulse-ring 2s infinite;">
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
    if not is_authenticated():
        st.error("⚠️ 请先登录系统")
        st.stop()

    # 运行当前选中的页面
    pg.run()


# ============================================================
# 入口
# ============================================================
if is_authenticated():
    main_app()
else:
    login_page()