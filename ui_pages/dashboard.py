import streamlit as st
import pandas as pd
from datetime import datetime

from utils.database import load_data_from_db
from utils.common import format_size
from config import COLUMN_MAPPING, REVERSE_MAPPING

def dashboard():

    try:
        df = load_data_from_db()
        # 确保时间列格式正确
        df['capture_time'] = pd.to_datetime(df['capture_time'])
    except Exception as e:
        st.error("无法连接数据库，请检查配置。")
        st.stop()

    # ================= 基础筛选 (常用) =================
    st.sidebar.markdown("---")
    st.sidebar.header("基础筛选")

    if 'FolderName' in df.columns:
        # 获取列表并去重
        all_folders = list(df['FolderName'].dropna().unique())
        all_folders.sort()

        folder_filter = st.sidebar.multiselect("📂 来源文件夹", all_folders, placeholder="全部文件夹")
    else:
        folder_filter = []

    available_types = list(df['FileType'].dropna().unique())
    selected_types = st.sidebar.multiselect(
        "🗃️ 文件类型筛选",
        options=available_types,
        default=available_types
    )
    search_txt = st.sidebar.text_input("按备注信息搜索")
    

    min_date = df['capture_time'].min().date() if not df.empty else datetime.today().date()
    max_date = df['capture_time'].max().date() if not df.empty else datetime.today().date()
    date_range = st.sidebar.date_input("📅 拍摄日期 ", (min_date, max_date))
    include_none_date = st.sidebar.checkbox(
        "包含无时间数据",
        value=True
    )

    models = ["全部"] + list(df['DroneModel'].dropna().unique())
    model_filter = st.sidebar.selectbox("🚁 机型", models)

    versions = ["全部"] + list(df['Version'].dropna().unique())
    version_filter = st.sidebar.selectbox("⚙ 版本", versions)

    rtk_filter = st.sidebar.radio("📡 RTK状态", ["全部", "固定解 (Fixed)", "非固定解"])

    # --- 应用基础筛选 ---
    df_filtered = df.copy()

    if isinstance(date_range, tuple) and len(date_range) == 2:
        if include_none_date:
            df_filtered = df_filtered[
                ((df_filtered['capture_time'].dt.date >= date_range[0]) &
                    (df_filtered['capture_time'].dt.date <= date_range[1])) |
                df_filtered['capture_time'].isna()
                ]
        else:
            df_filtered = df_filtered[
                (df_filtered['capture_time'].dt.date >= date_range[0]) &
                (df_filtered['capture_time'].dt.date <= date_range[1])
                ]

    if selected_types:
        df_filtered = df_filtered[df_filtered['FileType'].isin(selected_types)]
    
    if search_txt:
        df_filtered = df_filtered[
            #df_filtered['filename'].str.contains(search_txt, case=False, na=False) | 
            df_filtered['mark_note'].str.contains(search_txt, case=False, na=False)
        ]

    if model_filter != "全部":
        df_filtered = df_filtered[df_filtered['DroneModel'] == model_filter]

    if version_filter != "全部":
        df_filtered = df_filtered[df_filtered['Version'] == version_filter]

    if rtk_filter == "固定解 (Fixed)":
        df_filtered = df_filtered[df_filtered['RtkFlag'] == 50]
    elif rtk_filter == "非固定解":
        df_filtered = df_filtered[df_filtered['RtkFlag'] != 50]

    if folder_filter:
        df_filtered = df_filtered[df_filtered['FolderName'].isin(folder_filter)]

    # 顶部UI

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    numeric_columns = {
        "绝对高度 (米)": "AbsoluteAltitude",
        "相对高度 (米)": "RelativeAltitude",
        "无人机纬度": "GpsLatitude",
        "无人机经度": "GpsLongitude",

        "文件大小 (字节)": "FileSize",

        "云台横滚角 (Gimbal Roll)": "GimbalRollDegree",
        "云台俯仰角 (Gimbal Pitch)": "GimbalPitchDegree",
        "云台偏航角 (Gimbal Yaw)": "GimbalYawDegree",

        "机身横滚 (Flight Roll)": "FlightRollDegree",
        "机身俯仰 (Flight Pitch)": "FlightPitchDegree",
        "机身偏航 (Flight Yaw)": "FlightYawDegree",

        "飞行速度X (m/s)": "FlightXSpeed",
        "飞行速度Y (m/s)": "FlightYSpeed",
        "飞行速度Z (m/s)": "FlightZSpeed",

        "RTK 高度误差 (StdHgt)": "RtkStdHgt",
        "RTK 经度误差 (StdLon)": "RtkStdLon",
        "RTK 纬度误差 (StdLat)": "RtkStdLat",

        "激光测距距离 (米)": "LRFTargetDistance"

    }

    # 让用户选择要筛选哪些属性
    selected_filters = st.multiselect(
        "👇 请选择需要筛选的属性 (支持多选)",
        options=list(numeric_columns.keys()),
        default=[]  # 默认选中
    )

    # 动态生成输入框并执行筛选
    if selected_filters:
        with st.container():
            st.markdown("---")
            cols = st.columns(2)
            for i, label in enumerate(selected_filters):
                col_name = numeric_columns[label]

                # 检查该列是否存在于数据中 (防止数据库缺字段报错)
                if col_name not in df_filtered.columns:
                    st.warning(f"数据库中缺少字段：{col_name}，跳过筛选。")
                    continue

                # 获取当前数据的最大最小值，作为默认参考
                curr_min = float(df_filtered[col_name].min()) if not df_filtered.empty else 0.0
                curr_max = float(df_filtered[col_name].max()) if not df_filtered.empty else 100.0

                with cols[i % 2]:
                    st.markdown(f"**{label}**")
                    c_min, c_max = st.columns(2)
                    val_min = c_min.number_input(f"最小值", value=curr_min, key=f"min_{col_name}")
                    val_max = c_max.number_input(f"最大值", value=curr_max, key=f"max_{col_name}")

                # 使用一行三列布局：标签 | 最小值输入 | 最大值输入
                # c1, c2, c3 = st.columns([1, 2, 2])

                # with c1:
                #    st.markdown(f"**{label}**")
                #    st.caption(f"当前范围: {current_min:.2f} ~ {current_max:.2f}")

                # with c2:
                # 使用 number_input 允许用户精确输入
                # 默认值设为极值，这样默认不进行过滤
                #    val_min = st.number_input(f"最小 {label}", value=current_min, key=f"min_{col_name}")

                # with c3:
                #    val_max = st.number_input(f"最大 {label}", value=current_max, key=f"max_{col_name}")

                # --- 立即执行筛选逻辑 ---
                df_filtered = df_filtered[
                    (df_filtered[col_name] >= val_min) &
                    (df_filtered[col_name] <= val_max)
                    ]
            st.markdown("---")

    kpi1.metric("📸 筛选结果", f"{len(df_filtered)} 张")

    total_size = df_filtered['FileSize'].sum() if 'FileSize' in df_filtered.columns else 0
    kpi2.metric("💾 占用空间", format_size(total_size))

    kpi3.download_button(
        label="📥 导出数据 (CSV)",
        data=df_filtered.to_csv(index=False).encode('utf-8-sig'),
        file_name=f'dji_filter_result.csv',
        mime='text/csv'
    )

    if kpi4.button("🗺️ 同步筛选结果到地图", use_container_width=True):
        st.session_state['shared_map_data'] = df_filtered
        st.toast("✅ 数据已同步！请点击左侧侧边栏切换到 '遥感采样点地图' 查看。", icon="🚀")

    # ================= 4. 数据表格 =================
    # st.subheader(f"📄 数据明细")
    # 获取所有可用列
    all_cols = list(df.columns)
    # 定义默认列
    # default_cols = [
    #    'filename', 'capture_time', 'FileSize', 'Version', 'ImageSource', 'DroneModel', 'DroneSerialNumber',
    #    'CameraSerialNumber', 'FlightLineInfo',
    #    "AbsoluteAltitude", "RelativeAltitude", "GpsLatitude", "GpsLongitude", "GimbalRollDegree", "GimbalPitchDegree",
    #    "GimbalYawDegree", "FlightRollDegree", "FlightPitchDegree", "FlightYawDegree", "FlightXSpeed", "FlightYSpeed",
    #    "FlightZSpeed", "RtkStdHgt", "RtkStdLon", "RtkStdLat", "LRFTargetDistance",
    #    'GpsStatus', 'AltitudeType', 'created_at'
    # ]
    print(selected_types)
    if selected_types == ['.mp4']:
        default_cols = [
            'filename', 'capture_time', 'FileSize', 'FullPath',
            "FileHash", 'VideoDuration', 'VideoFrameRate', 'VideoWidth', 'VideoHeight'
        ]
    elif search_txt:
        default_cols = [
            'filename', 'mark_note', 'capture_time', 'FileSize', 'FullPath',
            "AbsoluteAltitude", "RelativeAltitude", "GpsLatitude", "GpsLongitude", "GimbalRollDegree",
            "GimbalPitchDegree",
            "GimbalYawDegree", "FlightRollDegree", "FlightPitchDegree", "FlightYawDegree", "FlightXSpeed",
            "FlightYSpeed",
            "FlightZSpeed",
            'DroneSerialNumber', 'CameraSerialNumber', 'FlightLineInfo'
        ]
    else:
        default_cols = [
            'filename', 'capture_time', 'FileSize', 'FullPath',
            "AbsoluteAltitude", "RelativeAltitude", "GpsLatitude", "GpsLongitude", "GimbalRollDegree",
            "GimbalPitchDegree",
            "GimbalYawDegree", "FlightRollDegree", "FlightPitchDegree", "FlightYawDegree", "FlightXSpeed",
            "FlightYSpeed",
            "FlightZSpeed",
            'DroneSerialNumber', 'CameraSerialNumber', 'FlightLineInfo'
        ]
    # 确保默认列真实存在于数据中
    default_cols = [c for c in default_cols if c in all_cols]

    all_display_options = [COLUMN_MAPPING.get(c, c) for c in all_cols]
    default_display_options = [COLUMN_MAPPING.get(c, c) for c in default_cols]

    with st.expander("点击调整表格显示的列   (Shift+鼠标滚轮可查看全部列)", expanded=False):
        # 多选组件
        selected_display_cols = st.multiselect(
            "可在此处调整列的显示范围和顺序：",
            options=all_display_options,
            default=default_display_options
        )

    # 渲染表格
    if not df_filtered.empty:
        final_db_cols = []
        for c_cn in selected_display_cols:
            c_en = REVERSE_MAPPING.get(c_cn, c_cn)
            if c_en in df_filtered.columns:
                final_db_cols.append(c_en)

        display_df = df_filtered[final_db_cols].copy()

        if 'FileSize' in display_df.columns:
            display_df['FileSize'] = display_df['FileSize'].apply(format_size)

        display_df = display_df.rename(columns=COLUMN_MAPPING)

        pinned_col_name = COLUMN_MAPPING.get('filename', '📄 文件名')

        table_height = 600

        st.dataframe(
            display_df,
            use_container_width=True,  # 撑满宽度
            height=table_height,  # 固定高度，保证滚动条可见
            hide_index=False,  # 显示索引
        )
    else:
        st.warning("当前筛选条件下没有数据。")