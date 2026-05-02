"""喔图工具函数"""

import os
import re
import math
from urllib.parse import urlparse, unquote


def format_size(size_bytes: int) -> str:
    """字节数转人类可读格式"""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    unit_index = int(math.floor(math.log(size_bytes, 1024)))
    unit_index = min(unit_index, len(units) - 1)
    size = size_bytes / (1024 ** unit_index)
    return f"{size:.1f} {units[unit_index]}"


def format_speed(speed_bytes: float) -> str:
    """速度格式化"""
    return f"{format_size(int(speed_bytes))}/s"


def extract_ext_from_url(url: str) -> str:
    """从URL提取扩展名"""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    clean_path = path.split("?")[0]
    if "." in os.path.basename(clean_path):
        ext = os.path.splitext(clean_path)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"):
            return ext
    return ".jpg"


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """清理文件名"""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip(" .")
    filename = re.sub(r'\s+', ' ', filename)
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    return filename or "unnamed"
