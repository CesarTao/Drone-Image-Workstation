import exifread
import re


def parse_dji_image(file_path):
    """
    解析大疆无人机图片的 EXIF 和 XMP 信息
    """
    data = {}

    # 1. 读取标准 EXIF 信息
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)

            # --- 基础信息 ---
            data['文件名'] = file_path.split('/')[-1]
            data['相机型号'] = str(tags.get('Image Model', '未知'))
            data['拍摄时间'] = str(tags.get('EXIF DateTimeOriginal', '未知'))

            # --- 图像尺寸 (宽 x 高) ---
            # 优先从 EXIF 读取，如果不存在则标记未知
            width = tags.get('EXIF ExifImageWidth')
            height = tags.get('EXIF ExifImageLength')
            data['分辨率'] = f"{width} x {height}" if width and height else "未知"

            # --- GPS 信息处理 ---
            if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                lat_ref = str(tags.get('GPS GPSLatitudeRef', 'N'))
                lat = tags.get('GPS GPSLatitude')
                lon_ref = str(tags.get('GPS GPSLongitudeRef', 'E'))
                lon = tags.get('GPS GPSLongitude')

                data['纬度'] = convert_to_degrees(lat) * (-1 if lat_ref == 'S' else 1)
                data['经度'] = convert_to_degrees(lon) * (-1 if lon_ref == 'W' else 1)

                alt_tag = tags.get('GPS GPSAltitude')
                if alt_tag.values:
                    val = alt_tag.values[0]
                    altitude_meters = val.num / val.den
                    data['GPS高度'] = f"{altitude_meters:.3f} 米"
                else:
                    data['GPS高度'] = "0 米"
            else:
                data['纬度'] = None
                data['经度'] = None

    except Exception as e:
        print(f"读取 EXIF 失败: {e}")
        return None

    # 2. 读取大疆 XMP 扩展信息 (提取云台角度等)
    # 大疆将特定数据以 XML 格式写入文件头部，我们使用二进制读取并正则匹配
    try:
        with open(file_path, 'rb') as f:
            # 读取前 50KB 数据通常已包含 XMP 信息
            binary_content = f.read(50000)
            try:
                content_str = binary_content.decode('utf-8', errors='ignore')
            except:
                content_str = ""

            # 定义需要提取的 XMP 标签 (根据需要添加)
            # GimbalPitchDegree: 云台俯仰角 (通常 -90 是垂直向下)
            # GimbalYawDegree: 云台偏航角 (机头朝向)
            # AbsoluteAltitude: 绝对高度
            # RelativeAltitude: 相对起飞点高度
            xmp_tags = {
                '云台俯仰角(Pitch)': r'drone-dji:GimbalPitchDegree="([\d\.\-\+]+)"',
                '云台偏航角(Yaw)': r'drone-dji:GimbalYawDegree="([\d\.\-\+]+)"',
                '云台横滚角(Roll)': r'drone-dji:GimbalRollDegree="([\d\.\-\+]+)"',
                '绝对高度': r'drone-dji:AbsoluteAltitude="([\d\.\-\+]+)"',
                '相对高度': r'drone-dji:RelativeAltitude="([\d\.\-\+]+)"'
            }

            for key, pattern in xmp_tags.items():
                match = re.search(pattern, content_str)
                if match:
                    data[key] = float(match.group(1))
                else:
                    data[key] = "未找到"

    except Exception as e:
        print(f"读取 XMP 失败: {e}")

    return data


def convert_to_degrees(value):
    """
    辅助函数：将 EXIF 的 GPS (度, 分, 秒) 格式转换为十进制格式
    """
    if not value:
        return 0.0
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)
    return d + (m / 60.0) + (s / 3600.0)


# --- 主程序入口 ---
if __name__ == "__main__":
    # 请将此处替换为你的图片路径
    image_path = "Z:/无人机/临时20251227/三林/2025年11月"

    # 注意：如果没有实际图片，请确保路径存在或处理异常
    import os

    if os.path.exists(image_path):
        result = parse_dji_image(image_path)

        if result:
            print("-" * 30)
            print(f"图片信息解析结果: {result['文件名']}")
            print("-" * 30)
            print(f"相机型号 : {result['相机型号']}")
            print(f"分辨率   : {result['分辨率']}")
            print(f"拍摄时间 : {result['拍摄时间']}")
            print(f"GPS 坐标（经纬度） : ({result['纬度']:.6f}, {result['经度']:.6f})")
            print(f"GPS 高度 : {result['GPS高度']:}")
            print("-" * 30)
            print("--- 大疆特有信息 (XMP) ---")
            print(f"云台横滚角 (Roll) : {result['云台横滚角(Roll)']}°")
            print(f"云台俯仰角 (Pitch) : {result['云台俯仰角(Pitch)']}°")
            print(f"云台偏航角 (Yaw)   : {result['云台偏航角(Yaw)']}°")
            print(f"绝对起飞高度       : {result['绝对高度']} 米")
            print(f"相对起飞高度       : {result['相对高度']} 米")
            print("-" * 30)
    else:
        print(f"错误: 找不到文件 {image_path}，请修改代码中的图片路径。")