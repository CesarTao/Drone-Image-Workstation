import streamlit as st

from ui_pages import dashboard, map, add_data, ai_helper, file_tag, flight_task
from ui_pages.dashboard import dashboard
from ui_pages.map import render_map
from ui_pages.add_data import single_parser, multi_parser
from ui_pages.ai_helper import ai_helper
from ui_pages.file_tag import file_tag
from ui_pages.flight_task import flight_task


import streamlit as st

def render_header(system_name, current_page):
    
    # 配色方案
    header_bg = "#F0F2F6"
    main_color = "#1E1E1E"
    sub_color = "#555555"
    separator_color = "#B0B0B0"

    st.markdown(f"""
        <style>
            /* 1. 修改原生 Header 背景 */
            header[data-testid="stHeader"] {{
                background-color: {header_bg} !important;
                border-bottom: 1px solid #d6d6d8;
                height: 75px;
            }}

            /* 2. 创建一个悬浮的标题容器  */
            .title-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 75px;
                display: flex;
                align-items: center;
                justify-content: center; /* 居中对齐 */
                z-index: 999992; /* 比原生 Header 高 */
                pointer-events: none;
                font-family: "Source Sans Pro", sans-serif;
            }}

            /* 3. 一级标题样式 */
            .main-title {{
                font-size: 25px;
                font-weight: 700; /* 加粗 */
                color: {main_color};
                margin-right: 10px;
            }}

            /* 4. 分隔符样式 */
            .separator {{
                font-size: 18px;
                color: {separator_color};
                margin-right: 10px;
                font-weight: 300;
            }}

            /* 5. 二级标题样式 */
            .sub-title {{
                font-size: 25px;
                font-weight: 400; /* 常规粗细 */
                color: {sub_color};
            }}

            /* 6. 隐藏干扰元素 */
            div[data-testid="stDecoration"] {{ display: none; }}
            
            /* 7. 布局调整 */
            .block-container {{ padding-top: 80px !important; }}
        </style>

        <div class="title-container">
            <span class="main-title">{system_name}</span>
            <span class="separator">/</span> <span class="sub-title">{current_page}</span>
        </div>
    """, unsafe_allow_html=True)




st.set_page_config(page_title="无人机数据管理平台", layout="wide", page_icon="🚁")


st.sidebar.title("🚁 功能菜单")
app_mode = st.sidebar.radio("功能菜单", [
    "🔍 航拍数据信息提取",
    "📂 航拍数据信息批量提取",
    "🌏 航拍数据采样点地图",
    "📊 航拍数据浏览与查询",
    "🧠 航拍数据AI智能查询",
    "🗃️ 航拍数据分类管理",
    "✈️ 飞行任务时长统计"
],
label_visibility="collapsed")

render_header("🚁无人机数据管理平台", app_mode)

if app_mode == "📊 航拍数据浏览与查询":
    dashboard()
elif app_mode == "🌏 航拍数据采样点地图":
    render_map()
elif app_mode == "🔍 航拍数据信息提取":
    single_parser()
elif app_mode == "📂 航拍数据信息批量提取":
    multi_parser()
elif app_mode == "🧠 航拍数据AI智能查询":
    ai_helper()
elif app_mode == "🗃️ 航拍数据分类管理":
    file_tag()
elif app_mode == "✈️ 飞行任务时长统计":
    flight_task()