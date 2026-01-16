import re


def explore_dji_tags(file_path):
    """
    提取并打印所有大疆特有的 XMP 标签
    """
    try:
        with open(file_path, 'rb') as f:
            # 读取头部 30KB 数据通常足够包含 XMP
            content = f.read(30000)

            # 解码，忽略错误
            try:
                content_str = content.decode('utf-8', errors='ignore')
            except:
                return

            # 正则表达式：匹配 drone-dji:属性名="属性值"
            # 格式例如: drone-dji:FlightRollDegree="-2.3"
            pattern = r'drone-dji:(\w+)="([^"]+)"'

            matches = re.findall(pattern, content_str)

            print(f"--- 在 {file_path} 中找到 {len(matches)} 个大疆标签 ---")
            for key, value in matches:
                # 打印每一个找到的属性
                print(f"{key:<25} : {value}")

    except Exception as e:
        print(f"读取错误: {e}")


# 使用示例
if __name__ == "__main__":
    explore_dji_tags("C:/Users/admin/PyCharmMiscProject/DJI_20251015104354_0012_W.jpeg")


'''参数名,功能解释
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
FlightLineInfo,当前飞行航线/任务的唯一识别 ID。'''