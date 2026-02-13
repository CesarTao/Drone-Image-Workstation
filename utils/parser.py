import streamlit as st
import os
import re
import exifread
from datetime import datetime
import re
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

from utils.common import calculate_md5


def parse_dji_metadata(file_stream, filename=None, full_path=None):  # 读取和解析
    folder_name = None
    current_hash = None

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
        "FileHash": current_hash, 'FullPath': full_path, 'FileType': 'Unknown',
        'VideoDuration': None, 'VideoFrameRate': None, 'VideoWidth': None, 'VideoHeight': None
    }

    if full_path:
        current_hash = calculate_md5(full_path)
        try:
            folder_name = os.path.basename(os.path.dirname(full_path))
        except:
            folder_name = "Unknown"
    else:
        current_hash = calculate_md5(file_stream)

    if full_path and os.path.exists(full_path):
        data['FullPath'] = os.path.abspath(full_path)  # 确保是绝对路径
        # data['FileSize'] = os.path.getsize(full_path)
        data['FolderName'] = os.path.basename(os.path.dirname(full_path))
        data['FileHash'] = calculate_md5(full_path)

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

        ext = os.path.splitext(data['filename'])[1].lower()
        if ext in ['.jpg', '.jpeg']:
            data['FileType'] = ext
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

        elif ext in ['.mp4', '.mov']:
            data['FileType'] = ext

            video_path_to_parse = None
            temp_file = None

            if full_path:
                video_path_to_parse = full_path
            elif hasattr(file_stream, 'read'):
                import tempfile
                file_stream.seek(0)
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tfile.write(file_stream.read())
                tfile.close()
                video_path_to_parse = tfile.name
                temp_file = tfile.name

            data['FileHash'] = calculate_md5(full_path)

            if video_path_to_parse:
                try:
                    parser = createParser(video_path_to_parse)
                    if parser:
                        with parser:
                            metadata = extractMetadata(parser)
                            if metadata:
                                if metadata.has('creation_date'):
                                    creation_date = metadata.get('creation_date')
                                    if creation_date.year <= 2010:
                                        data['capture_time'] = None
                                    else:
                                        from datetime import timedelta
                                        data['capture_time'] = creation_date + timedelta(hours=8)  # 修正 UTC+8

                                if metadata.has('width') and metadata.has('height'):
                                    data['VideoWidth'] = metadata.get('width')
                                    data['VideoHeight'] = metadata.get('height')

                                if metadata.has('duration'):
                                    duration_delta = metadata.get('duration')
                                    data['VideoDuration'] = round(duration_delta.total_seconds(), 2)

                                if metadata.has('frame_rate'):
                                    data['VideoFrameRate'] = metadata.get('frame_rate')

                except Exception as e:
                    print(f"hachoir 解析失败: {e}")

                finally:
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)

        # 关闭文件流
        if isinstance(file_stream, str) and not file_stream.closed:
            file_stream.close()

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