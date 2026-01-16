import os
import re
import exifread
import mysql.connector
from tqdm import tqdm
from datetime import datetime

# ================= 配置区域 =================
DB_CONFIG = {
    'host': 'localhost',  # 数据库地址
    'user': 'root',  # 用户名
    'password': '123456',  # 密码
    'database': 'dji_data'  # 数据库名
}

# IMAGE_FOLDER = 'Z:/无人机/临时20251227/三林/2025年11月'  # 图片文件夹路径
IMAGE_FOLDER = 'C:/Users/admin/Desktop/photos'


# ===========================================

def parse_dji_metadata(file_path):
    """
    解析单张图片，返回一个清洗好的字典，准备入库
    """
    # 初始化字典，使用您要求的字段名
    data = {
        'filename': os.path.basename(file_path),
        'capture_time': None,  # 保留捕获时间，虽未在列表中但通常必要

        # --- 基础信息 ---
        'Version': None,
        'ImageSource': None,
        'DroneModel': None,
        'DroneSerialNumber': None,
        'CameraSerialNumber': None,

        # --- GPS 位置 ---
        'GpsStatus': None,
        'AltitudeType': None,
        'GpsLatitude': None,
        'GpsLongitude': None,
        'AbsoluteAltitude': None,
        'RelativeAltitude': None,

        # --- 云台与飞行姿态 ---
        'GimbalRollDegree': None,
        'GimbalYawDegree': None,
        'GimbalPitchDegree': None,
        'FlightRollDegree': None,
        'FlightYawDegree': None,
        'FlightPitchDegree': None,
        'FlightXSpeed': None,
        'FlightYSpeed': None,
        'FlightZSpeed': None,
        'CamReverse': None,
        'GimbalReverse': None,

        # --- RTK 信息 ---
        'RtkFlag': None,
        'RtkStdLon': None,
        'RtkStdLat': None,
        'RtkStdHgt': None,

        # --- 作业信息 ---
        'SurveyingMode': None,
        'FlightLineInfo': None,

        # --- 激光测距 (LRF) ---
        'LRFStatus': None,
        'LRFTargetDistance': None,
        'LRFTargetLon': None,
        'LRFTargetLat': None,
        'LRFTargetAlt': None,
        'LRFTargetAbsAlt': None
    }

    try:
        # 1. 读取 EXIF (优先获取标准信息)
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)

            # --- 时间处理 ---
            if 'EXIF DateTimeOriginal' in tags:
                time_str = str(tags['EXIF DateTimeOriginal'])
                try:
                    data['capture_time'] = datetime.strptime(time_str, '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    pass

            # --- 型号 ---
            # 如果 XMP 中没有 DroneModel，这里作为保底
            data['DroneModel'] = str(tags.get('Image Model', 'Unknown'))

            # --- GPS 转换 (EXIF 优先级通常高于 XMP，因为它是标准) ---
            if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                data['GpsLatitude'] = convert_gps(tags['GPS GPSLatitude'], tags.get('GPS GPSLatitudeRef', 'N'))
                data['GpsLongitude'] = convert_gps(tags['GPS GPSLongitude'], tags.get('GPS GPSLongitudeRef', 'E'))

            # --- GPS 高度 (EXIF中的是绝对高度) ---
            if 'GPS GPSAltitude' in tags:
                val = tags['GPS GPSAltitude'].values[0]
                data['AbsoluteAltitude'] = float(val.num) / float(val.den)

        # 2. 读取 XMP (大疆特有数据)
        with open(file_path, 'rb') as f:
            # 读取前 50KB 通常足够包含 XMP 信息
            content_str = f.read(50000).decode('utf-8', errors='ignore')

            # 定义提取映射关系 (Regex -> DB Field)
            # 区分字符串、浮点数、整数的正则
            re_str = r'="{}"="([^"]+)"'  # 匹配字符串
            re_num = r'="{}"="([\d\.\-\+]+)"'  # 匹配数字(浮点/整型)

            # 映射表：(字段名, XMP标签名, 类型转换函数)
            # 如果 XMP 标签名和字段名一致，可以简化，这里为了清晰全部列出
            xmp_map = [
                # 字符串类型
                ('Version', 'Version', str),
                ('ImageSource', 'ImageSource', str),
                ('GpsStatus', 'GpsStatus', str),
                ('AltitudeType', 'AltitudeType', str),
                ('SurveyingMode', 'SurveyingMode', str),
                ('CameraSerialNumber', 'CameraSerialNumber', str),
                ('DroneModel', 'DroneModel', str),  # XMP 中也有型号，可能会覆盖 EXIF
                ('DroneSerialNumber', 'DroneSerialNumber', str),
                ('LRFStatus', 'LRFStatus', str),
                ('FlightLineInfo', 'FlightLineInfo', str),

                # 浮点类型
                ('RelativeAltitude', 'RelativeAltitude', float),
                ('GimbalRollDegree', 'GimbalRollDegree', float),
                ('GimbalYawDegree', 'GimbalYawDegree', float),
                ('GimbalPitchDegree', 'GimbalPitchDegree', float),
                ('FlightRollDegree', 'FlightRollDegree', float),
                ('FlightYawDegree', 'FlightYawDegree', float),
                ('FlightPitchDegree', 'FlightPitchDegree', float),
                ('FlightXSpeed', 'FlightXSpeed', float),
                ('FlightYSpeed', 'FlightYSpeed', float),
                ('FlightZSpeed', 'FlightZSpeed', float),
                ('RtkStdLon', 'RtkStdLon', float),
                ('RtkStdLat', 'RtkStdLat', float),
                ('RtkStdHgt', 'RtkStdHgt', float),
                ('LRFTargetDistance', 'LRFTargetDistance', float),
                ('LRFTargetLon', 'LRFTargetLon', float),
                ('LRFTargetLat', 'LRFTargetLat', float),
                ('LRFTargetAlt', 'LRFTargetAlt', float),
                ('LRFTargetAbsAlt', 'LRFTargetAbsAlt', float),
                # 补充：如果 EXIF 没读到绝对高度，尝试从 XMP 读
                ('AbsoluteAltitude', 'AbsoluteAltitude', float),

                # 整数类型
                ('CamReverse', 'CamReverse', int),
                ('GimbalReverse', 'GimbalReverse', int),
                ('RtkFlag', 'RtkFlag', int),
            ]

            for field, tag, dtype in xmp_map:
                # 构建正则: drone-dji:TagName="..."
                # 注意：有些标签可能是 drone-dji:TagName="..."
                pattern = r'drone-dji:' + tag + r'="([^"]+)"'

                match = re.search(pattern, content_str)
                if match:
                    val_str = match.group(1)
                    try:
                        # 仅当原来为空（如 EXIF 没读到）或者该字段不是通过 EXIF 读取的时才写入
                        # 或者强制覆盖（通常 XMP 的 DJI 数据更准，除了 Lat/Lon 建议保留 EXIF）
                        if data[field] is None or field not in ['GpsLatitude', 'GpsLongitude']:
                            data[field] = dtype(val_str)
                    except ValueError:
                        pass

    except Exception as e:
        print(f"解析出错 {file_path}: {e}")
        return None

    return data


def convert_gps(coord, ref):
    """ 辅助：将 GPS 度分秒转小数 """
    try:
        d = float(coord.values[0].num) / float(coord.values[0].den)
        m = float(coord.values[1].num) / float(coord.values[1].den)
        s = float(coord.values[2].num) / float(coord.values[2].den)
        val = d + (m / 60.0) + (s / 3600.0)
        if str(ref).upper() in ['S', 'W']:
            val = -val
        return val
    except:
        return 0.0


def save_to_db(data_list):
    """
    批量将数据插入 MySQL
    """
    if not data_list:
        return

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 动态生成 SQL 插入语句
        keys = list(data_list[0].keys())

        # SQL: INSERT INTO drone_photos (col1, col2) VALUES (%s, %s)
        cols = ", ".join(f"`{k}`" for k in keys)
        placeholders = ", ".join(["%s"] * len(keys))
        sql = f"INSERT INTO drone_photos ({cols}) VALUES ({placeholders})"

        # 准备 Values 列表
        values = []
        for item in data_list:
            row = [item.get(k) for k in keys]
            values.append(row)

        cursor.executemany(sql, values)
        conn.commit()
        # print(f"成功入库: {cursor.rowcount} 条记录")

    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def main():
    if not os.path.exists(IMAGE_FOLDER):
        print(f"错误：文件夹不存在 {IMAGE_FOLDER}")
        return

    print(f"开始扫描文件夹: {IMAGE_FOLDER}")

    batch_data = []

    # 使用 os.walk 递归扫描所有子目录
    # 为了让 tqdm 显示进度，我们先快速遍历一遍获取文件总数（可选，如果文件太多可以直接流式处理）
    all_files = []
    for root, dirs, files in os.walk(IMAGE_FOLDER):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg')):
                all_files.append(os.path.join(root, f))

    if not all_files:
        print("未找到图片文件")
        return

    with tqdm(total=len(all_files), desc="处理进度", unit="张") as pbar:
        for full_path in all_files:
            meta = parse_dji_metadata(full_path)

            if meta:
                batch_data.append(meta)

            pbar.update(1)

            # --- 批量入库逻辑 ---
            if len(batch_data) >= 100:
                pbar.set_postfix(status="写入DB...", refresh=False)
                save_to_db(batch_data)
                batch_data = []
                pbar.set_postfix(status="扫描中...", refresh=False)

    # 处理剩余数据
    if batch_data:
        save_to_db(batch_data)

    print("\n全部处理完成")


if __name__ == "__main__":
    main()