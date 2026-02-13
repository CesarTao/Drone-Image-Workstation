import pandas as pd
import os
import hashlib


def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"

def calculate_md5(file_input):
    """
    计算文件的 MD5 哈希值
    """
    hash_md5 = hashlib.md5()

    try:
        if isinstance(file_input, str) and os.path.exists(file_input):
            with open(file_input, "rb") as f:
                # 分块读取
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)

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

def color_wash(val):    # 把颜色清洗为中文
    if pd.isna(val): return "无"
    s = str(val)
    if "⚪" in s: return "无"
    if "🔴" in s: return "红"
    if "🟡" in s: return "黄"
    if "🟢" in s: return "绿"
    if "🔵" in s: return "蓝"
    return "无"

def standardize_color(user_input):  # 反向清洗
    if pd.isna(user_input) or str(user_input).strip() == "":
        return "⚪"  
    s = str(user_input).lower()
    if any(x in s for x in ['红', 'red', '严重', '报错', 'error', 'bad', '🔴']):
        return "🔴"
    if any(x in s for x in ['黄', 'yellow', '警告', '待定', 'warn', 'wait', '🟡']):
        return "🟡"
    if any(x in s for x in ['绿', 'green', '正常', '通过', 'ok', 'pass', 'good', '🟢']):
        return "🟢"
    if any(x in s for x in ['蓝', 'blue', '归档', '其他', 'other', 'archive', '🔵']):
        return "🔵"
    return "⚪"
