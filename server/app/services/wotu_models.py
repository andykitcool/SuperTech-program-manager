"""喔图照片同步数据模型"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class WotuPhotoStatus(str, Enum):
    """照片下载状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"    # 正在上传到云存储
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WotuTaskPhase(str, Enum):
    """任务阶段"""
    IDLE = "idle"
    SCRAPING = "scraping"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"     # 正在上传到云存储
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class WotuPhotoInfo:
    """照片信息"""
    id: str = ""
    url: str = ""
    thumb_url: str = ""
    filename: str = ""
    ext: str = ".jpg"
    size: int = 0
    shoot_time: str = ""
    width: int = 0
    height: int = 0
    status: WotuPhotoStatus = WotuPhotoStatus.PENDING
    download_duration: float = 0.0
    error_msg: str = ""
    index: int = 0
    tab: str = ""               # 所属选项卡
    category_id: str = ""
    category_name: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class WotuSyncStats:
    """同步统计"""
    phase: WotuTaskPhase = WotuTaskPhase.IDLE
    total_found: int = 0
    total_downloaded: int = 0
    total_uploaded: int = 0     # 已上传到云存储数
    total_failed: int = 0
    total_skipped: int = 0
    total_bytes: int = 0
    speed: float = 0.0
    scroll_count: int = 0
    current_tab: str = ""
    error_msg: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["phase"] = self.phase.value
        return d


@dataclass
class WotuSyncTask:
    """同步任务配置"""
    activity_id: int = 0
    url: str = ""
    concurrency: int = 5
    scroll_delay: int = 5
    no_new_stop_rounds: int = 3
    tab_mode: str = "current"       # "current" | "all"
    tab_subdir: bool = True
    selected_categories: list[dict] = field(default_factory=list)
    max_retries: int = 3
    timeout: int = 60
