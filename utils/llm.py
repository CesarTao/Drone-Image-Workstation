from openai import OpenAI
import re

from config import API_BASE, API_KEY


def generate_sql_from_ai(user_question, api_key=API_KEY, base_url=API_BASE):
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
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": f"你是一个专业的 MySQL 助手。{schema_info}"},
                {"role": "user", "content": f"请将此问题转换为 SQL: {user_question}"}
            ],
            temperature=0.1,
            stream=False
        )

        sql_content = response.choices[0].message.content.strip()

        # 清洗数据
        clean_sql = re.sub(r'```sql|```', '', sql_content).strip()

        return clean_sql, None

    except Exception as e:
        return None, f"AI 调用失败: {str(e)}"