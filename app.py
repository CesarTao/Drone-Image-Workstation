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
import hashlib
import streamlit.components.v1 as components
from openai import OpenAI
import re

# ================= 配置区域 =================
DB_CONFIG = {
    'host': '',
    'user': '',
    'password': '',
    'database': ''
}

# ================= 公共函数 =================
def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1024**2: return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3: return f"{size_bytes/(1024**2):.1f} MB"
    else: return f"{size_bytes/(1024**3):.2f} GB"


COLUMN_MAPPING = {  # 左边是数据库字段，右边展示的中文
        # 基础信息
        'filename': '📄 文件名',
        'capture_time': '📅 拍摄时间',
        'FileSize': '💾 文件大小',
        'DroneModel': '🚁 无人机型号',
        'Version': 'ℹ️ 协议版本',
        'ImageSource': '📷 镜头类型',
        'FolderName': '📂 来源文件夹',

        # 位置信息
        'GpsLatitude': '📍 纬度',
        'GpsLongitude': '📍 经度',
        'AbsoluteAltitude': '📏 绝对高度(m)',
        'RelativeAltitude': '🛫 相对高度(m)',
        'AltitudeType': '🗺️ 高度模式',

        # 姿态信息
        'GimbalPitchDegree': '📐 云台俯仰(Pitch)',
        'GimbalYawDegree': '📐 云台偏航(Yaw)',
        'GimbalRollDegree': '📐 云台横滚(Roll)',
        'FlightPitchDegree': '✈️ 机身俯仰',
        'FlightYawDegree': '✈️ 机身偏航',
        'FlightRollDegree': '✈️ 机身横滚',

        # 速度信息
        'FlightXSpeed': '🚀 速度X(东)',
        'FlightYSpeed': '🚀 速度Y(北)',
        'FlightZSpeed': '🚀 速度Z(升)',

        # RTK 与 精度
        'RtkFlag': '📡 RTK状态',
        'RtkStdLon': '🎯 经度误差',
        'RtkStdLat': '🎯 纬度误差',
        'RtkStdHgt': '🎯 高度误差',

        # 激光测距 (M30T)
        'LRFTargetDistance': '📏 激光测距(m)',
        'LRFTargetAbsAlt': '🏔️ 目标海拔(m)',
        'LRFTargetLat': '📍 目标纬度',
        'LRFTargetLon': '📍 目标经度',
        'LRFStatus': '🟢 LRF状态'
    }

    # 反向映射（用于通过中文找回英文列名）
REVERSE_MAPPING = {v: k for k, v in COLUMN_MAPPING.items()}


def calculate_md5(file_input):
    """
    计算文件的 MD5 哈希值 (数字指纹)
    支持: 文件路径(str) 或 文件流(BytesIO/Opened File)
    """
    hash_md5 = hashlib.md5()

    try:
        # 如果传入的是文件路径 (字符串)
        if isinstance(file_input, str) and os.path.exists(file_input):
            with open(file_input, "rb") as f:
                # 分块读取，防止一张图几百兆把内存撑爆
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)

        # 如果传入的是文件流
        else:
            # 记住当前指针位置
            original_pos = file_input.tell()
            file_input.seek(0)  # 回到开头

            # 分块读取
            for chunk in iter(lambda: file_input.read(4096), b""):
                hash_md5.update(chunk)

            file_input.seek(original_pos)

        return hash_md5.hexdigest()  # 返回 32位 字符串
    except Exception as e:
        return None


def parse_dji_metadata(file_stream, filename=None, full_path=None): # 读取和解析
    folder_name = None
    current_hash = None
    if full_path:
        current_hash = calculate_md5(full_path)
        try:
            folder_name = os.path.basename(os.path.dirname(full_path))
        except:
            folder_name = "Unknown"
    else:
        current_hash = calculate_md5(file_stream)

    data = {
        'filename': filename if filename else "Uploaded_Image",
        'capture_time': None, 'DroneModel': None, 'Version': None,
        'ImageSource': None, 'DroneSerialNumber': None, 'CameraSerialNumber': None,
        'GpsStatus': None, 'AltitudeType': None, 'GpsLatitude': None, 'GpsLongitude': None,
        'AbsoluteAltitude': None, 'RelativeAltitude': None, 'GimbalRollDegree': None,
        'GimbalYawDegree': None, 'GimbalPitchDegree': None, 'FlightRollDegree': None,
        'FlightYawDegree': None, 'FlightPitchDegree': None, 'FlightXSpeed': None,
        'FlightYSpeed': None, 'FlightZSpeed': None, 'CamReverse': None, 'GimbalReverse': None,
        'RtkFlag': None, 'RtkStdLon': None, 'RtkStdLat': None, 'RtkStdHgt': None,
        'SurveyingMode': None, 'FlightLineInfo': None, 'LRFStatus': None,
        'LRFTargetDistance': None, 'LRFTargetLon': None, 'LRFTargetLat': None,
        'LRFTargetAlt': None, 'LRFTargetAbsAlt': None, 'FileSize': 0, "FolderName": folder_name,
        "FileHash": current_hash
    }

    try:
        if isinstance(file_stream, str) and os.path.exists(file_stream):
            data['FileSize'] = os.path.getsize(file_stream)
            with open(file_stream, 'rb') as f:
                return parse_dji_metadata(f, filename=os.path.basename(file_stream))

            # 如果是 Streamlit 上传的文件流 / 打开的文件对象
        else:
            # 尝试获取大小
            try:
                # 移动指针到最后获取大小，再移回来
                file_stream.seek(0, os.SEEK_END)
                data['FileSize'] = file_stream.tell()
                file_stream.seek(0)
            except:
                pass

        # 1. 读取 EXIF
        # 注意：Streamlit上传的文件对象指针可能需要重置
        file_stream.seek(0)
        tags = exifread.process_file(file_stream, details=False)

        if 'EXIF DateTimeOriginal' in tags:
            try:
                data['capture_time'] = datetime.strptime(str(tags['EXIF DateTimeOriginal']), '%Y:%m:%d %H:%M:%S')
            except:
                pass

        data['DroneModel'] = str(tags.get('Image Model', 'Unknown'))

        if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
            data['GpsLatitude'] = convert_gps(tags['GPS GPSLatitude'], tags.get('GPS GPSLatitudeRef', 'N'))
            data['GpsLongitude'] = convert_gps(tags['GPS GPSLongitude'], tags.get('GPS GPSLongitudeRef', 'E'))

        if 'GPS GPSAltitude' in tags:
            val = tags['GPS GPSAltitude'].values[0]
            data['AbsoluteAltitude'] = float(val.num) / float(val.den)

        # 2. 读取 XMP
        file_stream.seek(0)
        content_str = file_stream.read(50000).decode('utf-8', errors='ignore')

        xmp_map = [
            ('Version', 'Version', str), ('ImageSource', 'ImageSource', str),
            ('GpsStatus', 'GpsStatus', str), ('AltitudeType', 'AltitudeType', str),
            ('SurveyingMode', 'SurveyingMode', str), ('CameraSerialNumber', 'CameraSerialNumber', str),
            ('DroneModel', 'DroneModel', str), ('DroneSerialNumber', 'DroneSerialNumber', str),
            ('LRFStatus', 'LRFStatus', str), ('FlightLineInfo', 'FlightLineInfo', str),
            ('RelativeAltitude', 'RelativeAltitude', float), ('GimbalRollDegree', 'GimbalRollDegree', float),
            ('GimbalYawDegree', 'GimbalYawDegree', float), ('GimbalPitchDegree', 'GimbalPitchDegree', float),
            ('FlightRollDegree', 'FlightRollDegree', float), ('FlightYawDegree', 'FlightYawDegree', float),
            ('FlightPitchDegree', 'FlightPitchDegree', float), ('FlightXSpeed', 'FlightXSpeed', float),
            ('FlightYSpeed', 'FlightYSpeed', float), ('FlightZSpeed', 'FlightZSpeed', float),
            ('RtkStdLon', 'RtkStdLon', float), ('RtkStdLat', 'RtkStdLat', float),
            ('RtkStdHgt', 'RtkStdHgt', float), ('LRFTargetDistance', 'LRFTargetDistance', float),
            ('LRFTargetLon', 'LRFTargetLon', float), ('LRFTargetLat', 'LRFTargetLat', float),
            ('LRFTargetAlt', 'LRFTargetAlt', float), ('LRFTargetAbsAlt', 'LRFTargetAbsAlt', float),
            ('AbsoluteAltitude', 'AbsoluteAltitude', float),
            ('CamReverse', 'CamReverse', int), ('GimbalReverse', 'GimbalReverse', int),
            ('RtkFlag', 'RtkFlag', int),
        ]

        for field, tag, dtype in xmp_map:
            pattern = r'drone-dji:' + tag + r'="([^"]+)"'
            match = re.search(pattern, content_str)
            if match:
                try:
                    val = match.group(1)
                    if data[field] is None or field not in ['GpsLatitude', 'GpsLongitude']:
                        data[field] = dtype(val)
                except:
                    pass
    except Exception as e:
        st.error(f"解析错误: {e}")
        return None
    return data


def convert_gps(coord, ref):
    try:
        d = float(coord.values[0].num) / float(coord.values[0].den)
        m = float(coord.values[1].num) / float(coord.values[1].den)
        s = float(coord.values[2].num) / float(coord.values[2].den)
        val = d + (m / 60.0) + (s / 3600.0)
        if str(ref).upper() in ['S', 'W']: val = -val
        return val
    except:
        return 0.0


def save_to_db(data_list):  # 储存到数据库
    if not data_list: return 0

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 提取当前批次所有的 FileHash
        incoming_hashes = [item.get('FileHash') for item in data_list if item.get('FileHash')]

        existing_hashes = set()

        # 如果这一批有哈希值，就去数据库批量查一下哪些已存在
        if incoming_hashes:
            placeholders_check = ', '.join(['%s'] * len(incoming_hashes))
            sql_check = f"SELECT FileHash FROM drone_photos WHERE FileHash IN ({placeholders_check})"

            cursor.execute(sql_check, tuple(incoming_hashes))

            # 将查到的结果转为集合 (Set)，方便快速查找
            result = cursor.fetchall()
            for row in result:
                existing_hashes.add(row[0])

        final_data_list = [
            item for item in data_list
            if item.get('FileHash') not in existing_hashes
        ]

        # 如果过滤完发现全是重复的，直接返回
        if not final_data_list:
            # print("本批次所有数据均为重复，跳过。")
            return 0

        keys = list(final_data_list[0].keys())
        cols = ", ".join(f"`{k}`" for k in keys)
        placeholders = ", ".join(["%s"] * len(keys))

        sql = f"INSERT INTO drone_photos ({cols}) VALUES ({placeholders})"

        # 构造 values 列表
        values = [[item.get(k) for k in keys] for item in final_data_list]

        cursor.executemany(sql, values)
        conn.commit()

        return cursor.rowcount

    except Exception as e:
        st.error(f"入库失败: {e}")
        return 0
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def clear_all_data():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE drone_photos")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"清空失败: {e}")
        return False


def load_data_from_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    query = "SELECT * FROM drone_photos ORDER BY capture_time DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def execute_raw_sql(sql_query): # 执行原始 SQL 语句并返回 DataFrame
    normalized_sql = sql_query.upper().strip()

    # 安全检查，暂未开启
    # forbidden_keywords = ['DROP', 'DELETE', 'UPDATE', 'TRUNCATE', 'ALTER', 'INSERT', 'GRANT']
    #for word in forbidden_keywords:
    #    # 简单的包含检查，防止 delete from ...
    #    if word in normalized_sql:
    #        return None, f"⚠️ 安全警告：为了保护数据，网页端禁止使用 {word} 命令。请使用数据库管理软件进行操作。"

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        # 使用 pandas 直接读取，它能自动处理列名和数据类型
        df_result = pd.read_sql(sql_query, conn)
        if 'FileSize' in df_result.columns:
            df_result['FileSize'] = df_result['FileSize'].apply(format_size)

        df_result = df_result.rename(columns=COLUMN_MAPPING)
        return df_result, None
    except Exception as e:
        return None, str(e)
    finally:
        if conn: conn.close()




def generate_sql_from_ai(user_question, api_key, base_url="https://api.deepseek.com"):
    """
    调用大模型，将自然语言转换为 SQL
    默认使用 DeepSeek API (兼容 OpenAI 格式)
    """
    if not api_key:
        return None, "API Key 未配置"

    client = OpenAI(api_key=api_key, base_url=base_url)

    schema_info = """
    这是 MySQL 数据库，主要内容是无人机航拍图片，包含一张表：

    Table: drone_photos (航拍照片表)
    - filename (文件名, e.g., 'DJI_001.JPG')
    - FolderName (项目/文件夹名, string)
    - FileSize (文件大小)
    - FileHash (哈希值)
    Version,大疆元数据协议的版本号。
ImageSource,拍摄该照片的镜头类型（Wide 为广角镜头）。
GpsStatus,GPS 定位模式（RTK 表示正在使用高精度差分定位）。
AltitudeType,高度参考系类型（RtkAlt 表示基于 RTK 的椭球高/绝对高度）。
GpsLatitude,拍摄时无人机所在的纬度。
GpsLongitude,拍摄时无人机所在的经度。
AbsoluteAltitude,无人机的绝对海拔高度（椭球高）。
RelativeAltitude,无人机相对于起飞点的相对高度。
GimbalRollDegree,云台横滚角（微调画面的水平线）。
GimbalYawDegree,云台偏航角（相机镜头的水平朝向）。
GimbalPitchDegree,云台俯仰角（相机上下角度，-90° 为垂直俯拍）。
FlightRollDegree,飞机机身横滚角（机身左右倾斜程度）。
FlightYawDegree,飞机机头朝向（机头指向的角度）。
FlightPitchDegree,飞机机身俯仰角（机身前后倾斜程度）。
FlightXSpeed,飞机在东西方向的飞行速度。
FlightYSpeed,飞机在南北方向的飞行速度。
FlightZSpeed,飞机在垂直方向的升降速度。
CamReverse,标记相机画面是否进行了倒置翻转（通常为 0）。
GimbalReverse,标记云台是否倒置安装（通常为 0）。
RtkFlag,RTK 信号质量标记（50 代表固定解 Fixed，精度最高）。
RtkStdLon,经度定位误差估值（标准差，数值越小越准）。
RtkStdLat,纬度定位误差估值（标准差）。
RtkStdHgt,高度定位误差估值（标准差）。
SurveyingMode,是否处于测绘作业模式标识。
CameraSerialNumber,相机模块的唯一硬件序列号。
DroneModel,无人机设备型号（M30T）。
DroneSerialNumber,无人机机身的唯一硬件序列号。
LRFStatus,激光测距模块的工作状态。
LRFTargetDistance,无人机到画面中心点的直线距离（激光测得）。
LRFTargetLon,画面中心点对应的地面目标经度。
LRFTargetLat,画面中心点对应的地面目标纬度。
LRFTargetAlt,画面中心点对应的目标相对高度。
LRFTargetAbsAlt,画面中心点对应的目标绝对海拔高度。
FlightLineInfo,当前飞行航线/任务的唯一识别 ID。


    要求：
    1. 仅输出 SQL 语句，不要输出 markdown 格式（如 ```sql），不要输出任何解释文字。
    2. 格式必须完全精确，用户能够复制你的输出，直接进行搜索
    3. 如果涉及模糊搜索，使用 LIKE '%keyword%'。
    4. 默认限制返回 20 条数据 (LIMIT 20)，除非用户指定了数量。
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # 或者 deepseek-coder
            messages=[
                {"role": "system", "content": f"你是一个专业的 MySQL 助手。{schema_info}"},
                {"role": "user", "content": f"请将此问题转换为 SQL: {user_question}"}
            ],
            temperature=0.1,  # 越低越严谨，写代码不需要太发散
            stream=False
        )

        # 获取 AI 返回的内容
        sql_content = response.choices[0].message.content.strip()

        # 2. 清洗数据 (防止 AI 还是忍不住加了 Markdown 符号)
        # 去掉 ```sql 和 ```
        clean_sql = re.sub(r'```sql|```', '', sql_content).strip()

        return clean_sql, None

    except Exception as e:
        return None, f"AI 调用失败: {str(e)}"





# ================= 主程序 UI =================

st.set_page_config(page_title="大疆无人机遥感照片解析工具", layout="wide", page_icon="🚁")

# 侧边栏导航
st.sidebar.title("🚁 功能菜单")
app_mode = st.sidebar.radio("", [
    "📊 数据展示与查询",
    "🌏 遥感采样点地图",
    "🔍 单张图片解析",
    "📂 文件夹批量入库",
    "🧠 数据库实验室"
])

if app_mode == "📊 数据展示与查询":

    try:
        df = load_data_from_db()
        # 确保时间列格式正确
        df['capture_time'] = pd.to_datetime(df['capture_time'])
    except Exception as e:
        st.error("无法连接数据库，请检查配置。")
        st.stop()

    # ================= 1. 基础筛选 (常用) =================
    st.sidebar.markdown("---")
    st.sidebar.header("基础筛选")

    if 'FolderName' in df.columns:
        # 获取列表并去重
        all_folders = list(df['FolderName'].dropna().unique())
        all_folders.sort()

        folder_filter = st.sidebar.multiselect("📂 来源文件夹", all_folders, placeholder="全部文件夹")
    else:
        folder_filter = []

    min_date = df['capture_time'].min().date() if not df.empty else datetime.today().date()
    max_date = df['capture_time'].max().date() if not df.empty else datetime.today().date()
    date_range = st.sidebar.date_input("📅 拍摄日期", (min_date, max_date))

    models = ["全部"] + list(df['DroneModel'].dropna().unique())
    model_filter = st.sidebar.selectbox("🚁 机型", models)

    versions = ["全部"] + list(df['Version'].dropna().unique())
    version_filter = st.sidebar.selectbox("⚙ 版本", versions)

    rtk_filter = st.sidebar.radio("📡 RTK状态", ["全部", "固定解 (Fixed)", "非固定解"])

    # --- 应用基础筛选 ---
    df_filtered = df.copy()


    if isinstance(date_range, tuple) and len(date_range) == 2:
        df_filtered = df_filtered[
            (df_filtered['capture_time'].dt.date >= date_range[0]) &
            (df_filtered['capture_time'].dt.date <= date_range[1])
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
    col_main, col_kpi = st.columns([1, 1], gap="medium")
    with col_main:
        st.title("🚀 航拍数据面板")
    with col_kpi:
        kpi1, kpi2, kpi3, kpi4= st.columns(4)


    numeric_columns = {
        "绝对高度 (米)": "AbsoluteAltitude",
        "相对高度 (米)": "RelativeAltitude",
        "无人机纬度" : "GpsLatitude",
        "无人机经度" : "GpsLongitude",

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

    # B. 让用户选择要筛选哪些属性
    selected_filters = st.multiselect(
        "👇 请选择需要筛选的属性 (支持多选)",
        options=list(numeric_columns.keys()),
        default=[]  # 默认选中
    )

    # C. 动态生成输入框并执行筛选
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

                with cols[i%2]:
                    st.markdown(f"**{label}**")
                    c_min, c_max = st.columns(2)
                    val_min = c_min.number_input(f"最小值", value=curr_min, key=f"min_{col_name}")
                    val_max = c_max.number_input(f"最大值", value=curr_max, key=f"max_{col_name}")

                # 使用一行三列布局：标签 | 最小值输入 | 最大值输入
                #c1, c2, c3 = st.columns([1, 2, 2])

                #with c1:
                #    st.markdown(f"**{label}**")
                #    st.caption(f"当前范围: {current_min:.2f} ~ {current_max:.2f}")

                #with c2:
                    # 使用 number_input 允许用户精确输入
                    # 默认值设为极值，这样默认不进行过滤
                #    val_min = st.number_input(f"最小 {label}", value=current_min, key=f"min_{col_name}")

                #with c3:
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
        # 1. 存入 session_state
        st.session_state['shared_map_data'] = df_filtered

        # 2. 提示用户
        st.toast("✅ 数据已同步！请点击左侧侧边栏切换到 '遥感采样点地图' 查看。", icon="🚀")

    # ================= 4. 数据表格 =================
    #st.subheader(f"📄 数据明细")
    # 获取所有可用列
    all_cols = list(df.columns)
    # 定义默认列
    #default_cols = [
    #    'filename', 'capture_time', 'FileSize', 'Version', 'ImageSource', 'DroneModel', 'DroneSerialNumber',
    #    'CameraSerialNumber', 'FlightLineInfo',
    #    "AbsoluteAltitude", "RelativeAltitude", "GpsLatitude", "GpsLongitude", "GimbalRollDegree", "GimbalPitchDegree",
    #    "GimbalYawDegree", "FlightRollDegree", "FlightPitchDegree", "FlightYawDegree", "FlightXSpeed", "FlightYSpeed",
    #    "FlightZSpeed", "RtkStdHgt", "RtkStdLon", "RtkStdLat", "LRFTargetDistance",
    #    'GpsStatus', 'AltitudeType', 'created_at'
    #]

    default_cols = [
        'filename', 'capture_time', 'FileSize',
        "AbsoluteAltitude", "RelativeAltitude", "GpsLatitude", "GpsLongitude", "GimbalRollDegree", "GimbalPitchDegree",
        "GimbalYawDegree", "FlightRollDegree", "FlightPitchDegree", "FlightYawDegree", "FlightXSpeed", "FlightYSpeed",
        "FlightZSpeed",
        'DroneSerialNumber','CameraSerialNumber', 'FlightLineInfo'
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
        # 1. 找出用户选了哪些列，并转回数据库字段名以提取数据
        final_db_cols = []
        for c_cn in selected_display_cols:
            # 尝试从反向映射里找英文名，找不到说明本来就是英文（未配置映射）
            c_en = REVERSE_MAPPING.get(c_cn, c_cn)
            if c_en in df_filtered.columns:
                final_db_cols.append(c_en)

        # 2. 截取数据
        display_df = df_filtered[final_db_cols].copy()

        # 3. 把文件大小数字转为 "MB" 字符串
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




elif app_mode == "🌏 遥感采样点地图":
    st.markdown("""
            <style>
                /* 1. 取消主内容区域的内边距 (上、下、左、右) */
                .block-container {
                    padding-top: 0rem !important;
                    padding-bottom: 0rem !important;
                    padding-left: 1rem !important; /* 保留一点左边距以免贴太紧 */
                    padding-right: 1rem !important;
                    max-width: 100% !important;
                }

                /* 2. (可选) 隐藏页面右上角的菜单按钮和顶栏，让视野更纯净 */
                header[data-testid="stHeader"] {
                    display: none;
                }

                /* 3. 调整地图容器的边框 */
                iframe {
                    border: none !important;
                }
            </style>
        """, unsafe_allow_html=True)
    st.title("🗺️ 采样点位分布")

    if 'shared_map_data' in st.session_state and not st.session_state['shared_map_data'].empty:
        # A. 优先使用传过来的筛选数据
        df = st.session_state['shared_map_data']
        data_source_text = "🔍 来自【数据查询】的筛选结果"
        is_filtered_view = True
    else:
        # B. 如果没有，则加载全量数据库
        try:
            df = load_data_from_db()
            data_source_text = "💾 全量数据库"
            is_filtered_view = False
        except:
            st.stop()


        # 侧边栏添加地图专属控制
    st.sidebar.markdown("---")
    st.sidebar.header("地图控制")

    # 1. 简单的侧边栏筛选 (为了方便看图，只留最核心的)
    # show_rtk_only = st.sidebar.checkbox("只显示 RTK 固定解", value=False)
    #map_style = st.sidebar.selectbox("地图风格", ["卫星/深色 (Satellite)", "街道/浅色 (Road)"])
    point_radius = st.sidebar.slider("轨迹点大小", 1, 20, 5)

    # 2. 数据处理
    map_df = df.copy()
    #if show_rtk_only:
    #    map_df = map_df[map_df['RtkFlag'] == 50]

    # 必须清除无效坐标
    map_df = map_df.dropna(subset=['GpsLatitude', 'GpsLongitude'])
    map_df = map_df[(map_df['GpsLatitude'] != 0) & (map_df['GpsLongitude'] != 0)]

    if map_df.empty:
        st.warning("当前没有包含 GPS 坐标的照片数据。")
    else:
        # 3. 动态计算地图中心和缩放
        # 取平均值作为中心
        mid_lat = map_df['GpsLatitude'].mean()
        mid_lon = map_df['GpsLongitude'].mean()
        if len(map_df) >=50:
            zoom_start = 10
        elif len(map_df) >=20:
            zoom_start = 12
        else:
            zoom_start = 16

        m = folium.Map(
            location=[mid_lat, mid_lon],
            zoom_start=zoom_start,
            control_scale=True,
            # 使用高德地图底图 (需要网络能访问高德)
            tiles='https://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}',
            attr='高德地图'
        )

        # 往地图上加点
        for index, row in map_df.iterrows():
            folium.CircleMarker(
                location=[row['GpsLatitude'], row['GpsLongitude']],
                radius=point_radius,
                color='red',
                fill=True,
                fill_color='red',
                tooltip=f"{row['filename']} (高度: {row['AbsoluteAltitude']}m)"
            ).add_to(m)

        # 在 Streamlit 中渲染
        st_folium(m, width=None, height=620)

        st.sidebar.info(f"当前地图展示了 {len(map_df)} 个轨迹点。")




elif app_mode == "🔍 单张图片解析":
    st.title("🔍 单张图片属性解析")
    uploaded_file = st.file_uploader("上传一张大疆航拍照片 (JPG)", type=['jpg', 'jpeg'])

    if uploaded_file is not None:
        # 解析
        meta = parse_dji_metadata(uploaded_file, uploaded_file.name)

        if meta:
            col_img, col_info = st.columns([1, 2])
            with col_img:
                st.image(uploaded_file, caption="预览图", use_container_width=True)

            with col_info:
                st.success("✅ 解析成功！")
                # 重点展示
                st.write("### 核心参数")
                st.write(f"**📍 坐标**: {meta['GpsLatitude']}, {meta['GpsLongitude']}")
                st.write(f"**📏 绝对高度**: {meta['AbsoluteAltitude']} 米")
                st.write(f"**📷 云台俯仰**: {meta['GimbalPitchDegree']}°")

                # RTK 徽章
                if meta['RtkFlag'] == 50:
                    st.success("RTK状态: FIXED (固定解 - 高精度)")
                else:
                    st.warning(f"RTK状态: {meta['RtkFlag']} (非固定解)")

            # 展示所有 JSON 数据
            with st.expander("查看所有 30+ 项原始属性", expanded=True):
                st.json(meta)
        else:
            st.error("无法提取元数据，请确认这是大疆原片。")



# --- 模块 4: 批量入库 ---
elif app_mode == "📂 文件夹批量入库":
    st.title("📂 本地文件夹批量入库")
    folder_path = st.text_input("请输入NAS文件夹路径", "")

    if st.button("开始扫描并入库"):
        if not os.path.exists(folder_path):
            st.error("路径不存在！")
        else:
            st.info(f"正在扫描: {folder_path} ...")
            all_files = []
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    if f.lower().endswith(('.jpg', '.jpeg')):
                        all_files.append(os.path.join(root, f))

            total = len(all_files)
            st.write(f"发现 {total} 张图片。")

            progress_bar = st.progress(0)
            status_text = st.empty()

            batch_data = []
            success_count = 0

            for i, full_path in enumerate(all_files):
                # 这里的 open 逻辑需要适配
                try:
                    with open(full_path, 'rb') as f:
                        meta = parse_dji_metadata(f, os.path.basename(full_path), full_path=full_path)
                        if meta:
                            batch_data.append(meta)
                except:
                    pass

                # 批量入库
                if len(batch_data) >= 50:
                    count = save_to_db(batch_data)
                    success_count += count
                    batch_data = []

                # 更新进度
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"正在处理 ({i + 1}/{total}): {os.path.basename(full_path)}")

            # 剩余入库
            if batch_data:
                count = save_to_db(batch_data)
                success_count += count

            st.success(f"🎉 全部完成！共成功入库 {success_count} 条记录。")

    st.sidebar.markdown("---")
    st.sidebar.header("数据库管理")

    # 使用 expander 把按钮藏起来，防止误触
    with st.sidebar.expander("🗑️ 清空数据库", expanded=False):
        st.warning("⚠️ 警告：此操作将 **永久删除** 数据库中的所有照片记录，且 **无法恢复**！")

        confirm_check = st.checkbox("确认清空", key="danger_check")

        if confirm_check:
            if st.button("🔴 立即清空所有数据", type="primary", use_container_width=True):
                with st.spinner("正在销毁数据..."):
                    if clear_all_data():
                        st.success("数据库已清空！")
                        import time

                        time.sleep(1)  # 停顿一下让用户看到成功提示
                        st.rerun()  # 刷新页面


# --- 模块 5: 数据库实验室 (SQL & AI) ---
elif app_mode == "🧠 数据库实验室":
    st.title("🧠 AI辅助与SQL查询")

    st.sidebar.markdown("---")
    st.sidebar.header("模式选择")
    sub_mode = st.sidebar.radio("✨ AI模式", ["🛠️ SQL手动查询", "🤖 AI智能辅助"])

    if sub_mode == "🛠️ SQL手动查询":
        st.markdown("### 👨‍💻 SQL控制台")
        result_container = st.container()
        st.caption("在此处输入标准的 MySQL 查询语句。")

        # 1. 布局：左边是输入框，右边是表结构参考 (防忘词)
        col_edit, col_schema = st.columns([3, 1])

        with col_schema:
            st.info("📚 属性名称参考")
            st.code("""
id, filename, Version
FilePath, FolderName
capture_time, created_time
GpsLatitude, GpsLongitude
AbsoluteAltitude, RelativeAltitude
FlightXSpeed, FlightYSpeed
DroneModel
FileHash
                """, language="text")



        with col_edit:
            # 默认给一个示例 SQL
            default_sql = """-- 示例：查询最近上传的 10 张照片
SELECT id, filename, capture_time, FolderName, AbsoluteAltitude 
FROM drone_photos 
ORDER BY capture_time DESC 
LIMIT 10;"""

            # SQL 输入区域 (高度调高一点)
            txt_sql = st.text_area("输入 SQL 脚本:", value=default_sql, height=250)

            # 执行按钮
            run_col1, run_col2 = st.columns([1, 4])
            with run_col1:
                btn_run = st.button("▶️ 执行查询", type="primary", use_container_width=True)
            with run_col2:
                st.caption("")

        # 2. 结果展示区域
        st.divider()
        if btn_run:
            if not txt_sql.strip():
                st.warning("请输入 SQL 语句。")
            else:
                with st.spinner("正在查询数据库..."):
                    df_res, error_msg = execute_raw_sql(txt_sql)

                    if error_msg:
                        st.error(f"❌ 执行失败: \n{error_msg}")
                    elif df_res is not None:
                        # 成功获取数据
                        with result_container:
                            st.success(f"✅ 查询成功！返回 {len(df_res)} 行记录。")
                            st.dataframe(df_res, use_container_width=True)
                            st.download_button(
                                label="📥 下载查询结果 (CSV)",
                                data=df_res.to_csv(index=False).encode('utf-8-sig'),
                                file_name=f"sql_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime='text/csv'
                            )

                    else:
                        st.info("查询执行成功，但没有返回数据（结果集为空）。")


    elif sub_mode == "🤖 AI智能辅助":
        st.markdown("### 🤖 AI 数据分析助手")
        st.caption("基于 DeepSeek V3/R1 模型。用自然语言提问，AI 自动生成 SQL 并执行。如果没有指定数量，默认显示20条数据。")
        api_key_input = ""
        api_base = "https://api.deepseek.com"


        chat_container = st.container()
        user_text = st.chat_input("请输入你的问题 (例如: 帮我找出高度大于100米的照片)")
        if user_text:
            with chat_container:
                st.chat_message("user").write(user_text)

                if not api_key_input:
                    st.chat_message("assistant").error("❌ API Key 未配置")
                else:
                    with st.spinner("🤖 AI 正在思考中..."):
                        generated_sql, err = generate_sql_from_ai(user_text, api_key_input, api_base)
                    if err:
                        st.chat_message("assistant").error(err)
                    else:
                        # 显示生成的 SQL (让用户确认，增加透明度)
                        msg = st.chat_message("assistant")
                        msg.caption("生成 SQL:")
                        msg.code(generated_sql, language="sql")

                        # C. 自动执行 SQL
                        df_result, db_err = execute_raw_sql(generated_sql)

                        if db_err:
                            msg.error(f"⚠️ SQL 执行报错: {db_err}")
                            msg.warning("可能是 AI 生成的字段名不对，请尝试换个问法。")
                        elif df_result is not None:
                            if df_result.empty:
                                sg.info("查询执行成功，但没有找到符合条件的数据。")
                            else:
                                msg.success(f"✅ 查询成功，共 {len(df_result)} 条结果：")
                                msg.dataframe(df_result, use_container_width=True)