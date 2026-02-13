
# ================= 配置区域 =================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'drone_photos'
}

API_KEY = "sk-e2b4bc48c985443fa8a4183b8a12d7fe"
API_BASE = "https://api.deepseek.com"
# ============================================

COLUMN_MAPPING = {  # 左边是数据库字段，右边展示的中文
    # 基础信息
    'filename': '📄 文件名',
    'capture_time': '📅 拍摄时间',
    'FileSize': '💾 文件大小',
    'FileType': '📂 类型',
    'DroneModel': '🚁 无人机型号',
    'Version': 'ℹ️ 协议版本',
    'ImageSource': '📷 镜头类型',
    'FolderName': '📂 来源文件夹',
    'FullPath': '🛣️ 完整路径',
    'mark_note': '备注信息',

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
    'LRFStatus': '🟢 LRF状态',

    # 视频信息
    'VideoDuration': '⏱️ 视频时长(s)',
    'VideoFrameRate': '🎞️ 帧率(FPS)',
    'VideoWidth': '↔️ 分辨率宽',
    'VideoHeight': '↕️ 分辨率高'
}

# 反向映射（用于通过中文找回英文列名）
REVERSE_MAPPING = {v: k for k, v in COLUMN_MAPPING.items()}