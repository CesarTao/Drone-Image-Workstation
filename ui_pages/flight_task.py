import streamlit as st
import pandas as pd
import mysql.connector
import os
import re
import exifread
from datetime import datetime
import pydeck as pdk
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MarkerCluster
import hashlib
import streamlit.components.v1 as components
from openai import OpenAI
import re
import cv2
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import time
import openpyxl
from streamlit_option_menu import option_menu

from config import DB_CONFIG
from utils.database import process_excel_to_db

def flight_task():
    #st.subheader("⏱️ 飞行任务时长数据库")
    st.sidebar.header("数据库管理")

    with st.sidebar.expander("🗑️ 清空数据库", expanded=False):
        st.warning("⚠️ 警告：此操作将 **永久删除** 数据库中的所有数据，且 **无法恢复**！")

        confirm_check = st.checkbox("确认清空", key="danger_check")

        if confirm_check:
            if st.button("🔴 立即清空所有数据", type="primary", use_container_width=True):
                with st.spinner("正在销毁数据..."):
                    try:
                        conn = mysql.connector.connect(**DB_CONFIG)
                        cursor = conn.cursor()
                        cursor.execute("TRUNCATE TABLE task_hours")
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        st.error(f"清空失败: {e}")

                    import time
                    time.sleep(1)  # 停顿一下让用户看到成功提示
                    st.rerun()  # 刷新页面
    with st.expander("📥 导入新的 Excel 统计表", expanded=True):
        uploaded_file = st.file_uploader("上传飞行任务记录表 (.xlsx)", type=["xlsx"])
        if uploaded_file and st.button("🚀 解析并入库"):
            count = process_excel_to_db(uploaded_file)
            if count > 0:
                st.success(f"处理完成！已新增 {count} 条数据。")
                time.sleep(1)  # 稍等一下让用户看到提示
                st.rerun()  # 刷新页面显示最新数据

    st.divider()
    st.subheader("📊 历史飞行任务数据")

    conn = mysql.connector.connect(**DB_CONFIG)
    if conn:
        # 读取数据
        df_tasks = pd.read_sql("SELECT * FROM task_hours ORDER BY created_at DESC", conn)
        conn.close()

        if not df_tasks.empty:
            # 简单统计
            col1, col2, col3 = st.columns(3)
            

            # 筛选器
            file_filter = st.multiselect("按来源文件筛选", df_tasks['source_filename'].unique())
            if file_filter:
                df_tasks = df_tasks[df_tasks['source_filename'].isin(file_filter)]

            min_date = df_tasks['task_date'].min() if not df_tasks.empty else datetime.today().date()
            max_date = df_tasks['task_date'].max() if not df_tasks.empty else datetime.today().date()
            date_range = st.sidebar.date_input("📅 任务日期 ", (min_date, max_date))
            df_filtered = df_tasks.copy()

            if isinstance(date_range, tuple) and len(date_range) == 2:
                df_task_date = pd.to_datetime(df_filtered['task_date'], errors='coerce')
                df_filtered = df_filtered[
                    (df_task_date >= pd.Timestamp(date_range[0])) &
                    (df_task_date <= pd.Timestamp(date_range[1]))
                    ]

            col1.metric("总记录数", len(df_filtered))
            col2.metric("总任务时长 (分钟)", f"{df_filtered['duration_minutes'].sum():.1f}")
            col3.metric("总任务时长 (小时)", f"{df_filtered['duration_minutes'].sum() / 60:.2f}")

            # 展示表格
            st.markdown("### 📋 详细数据列表")
            st.dataframe(
                df_filtered,
                use_container_width=True,
                hide_index=True,
                column_order=[
                    "task_date", "start_time", "end_time", "duration_minutes",
                    "source_filename", "created_at"
                ],
                column_config={
                    "id": st.column_config.NumberColumn("系统ID"),
                    "batch_id": "批次编号",

                    "source_filename": st.column_config.TextColumn("📄 来源文件", width="medium"),

                    "task_date": st.column_config.TextColumn("📅 任务日期", width="small"),

                    "start_time": st.column_config.TextColumn("🟢 开始时间", help="任务开始的具体时间点"),

                    "end_time": st.column_config.TextColumn("🔴 结束时间", help="任务结束的具体时间点"),

                    "duration_minutes": st.column_config.NumberColumn(
                        "⏳ 任务时长 (分钟)",
                        format="%.1f",  # 保留1位小数
                        help="自动计算的时长"
                    ),

                    "created_at": st.column_config.DatetimeColumn(
                        "📥 导入时间",
                        format="YYYY-MM-DD HH:mm"
                    ),
                },
                height=600
            )
        else:
            st.info("暂无飞行任务数据，请上传 Excel 进行导入。")