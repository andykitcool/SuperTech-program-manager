"""
蓝阔（链科）云打印 API 客户端
基于官方 API 文档: https://docs.liankenet.com/api_doc/
"""

import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# 默认 API 基础 URL
DEFAULT_API_BASE_URL = "https://cloud.liankenet.com/api"


class LankuoPrintError(Exception):
    """蓝阔云打印错误"""
    pass


class LankuoClient:
    """蓝阔云打印 API 客户端（基于官方 V3 API 文档）"""

    def __init__(self, config: dict):
        self.api_base_url = config.get("apiBaseUrl", DEFAULT_API_BASE_URL).rstrip("/")
        # 兼容：如果用户配置的是根域名，自动补 /api
        if not self.api_base_url.endswith("/api"):
            self.api_base_url += "/api"
        self.api_key = config.get("ApiKey", "")
        self.device_id = config.get("deviceId", "")
        self.device_key = config.get("deviceKey", "")
        self.device_port = config.get("devicePort", "1")
        self.printer_type = config.get("printerType", "1")
        self.printer_model = config.get("printerModel", "")
        self.target_ip = config.get("targetIp", "")

        # 打印参数（来自官方文档）
        self.dm_paper_size = config.get("dmPaperSize", "9")
        self.dm_orientation = config.get("dmOrientation", "1")
        self.dm_copies = config.get("dmCopies", 1)
        self.dm_color = config.get("dmColor", "2")
        self.dm_duplex = config.get("dmDuplex", "1")
        self.dm_default_source = config.get("dmDefaultSource", "")
        self.dm_media_type = config.get("dmMediaType", "")
        self.dm_print_quality = config.get("dmPrintQuality", "")
        self.jp_scale = config.get("jpScale", "fit")
        self.jp_auto_scale = config.get("jpAutoScale", "4")
        self.jp_auto_align = config.get("jpAutoAlign", "z5")
        self.jp_page_range = config.get("jpPageRange", "")
        self.html_kernel = config.get("htmlKernel", "chrometopdf")
        self.callback_url = config.get("callbackUrl", "")
        self.report_device_status = config.get("reportDeviceStatus", True)
        self.report_printer_status = config.get("reportPrinterStatus", True)
        self.err_limit_num = config.get("errLimitNum", 30)
        self.pdf_rev = config.get("pdfRev", False)
        self.jp_auto_rotate = config.get("jpAutoRotate", False)

        # 自定义纸张参数
        self.dm_paper_length = config.get("dmPaperLength", 0)
        self.dm_paper_width = config.get("dmPaperWidth", 0)

        # 缓存打印机信息
        self._printer_list_cache: Optional[list] = None
        self._printer_params_cache: Optional[dict] = None

    @property
    def _headers(self) -> dict:
        return {
            "ApiKey": self.api_key,
        }

    @property
    def _device_params(self) -> dict:
        return {
            "deviceId": self.device_id,
            "deviceKey": self.device_key,
        }

    def _handle_response(self, resp: httpx.Response) -> dict:
        """处理蓝阔API响应"""
        if resp.status_code >= 500:
            body_preview = resp.text[:500].strip()
            logger.error("蓝阔服务器错误 HTTP %s: %s", resp.status_code, body_preview or "<empty>")
            detail = body_preview[:180] if body_preview else "请稍后重试"
            raise LankuoPrintError(f"蓝阔服务器错误 (HTTP {resp.status_code}): {detail}")
        if resp.status_code in (401, 403):
            raise LankuoPrintError(f"蓝阔API认证失败 (HTTP {resp.status_code}), 请检查ApiKey")
        try:
            data = resp.json()
        except Exception:
            raise LankuoPrintError(f"蓝阔API返回非JSON响应 (HTTP {resp.status_code}): {resp.text[:200]}")

        # 官方文档: code == 200 表示成功
        if "code" in data and data["code"] != 200:
            raise LankuoPrintError(f"蓝阔API错误 (code={data['code']}): {data.get('msg', '')}")

        return data

    async def get_printer_list(self, use_cache: bool = True) -> list:
        """
        第一步：获取设备上的打印机列表
        GET /api/external_api/printer_list?deviceId=xxx&deviceKey=xxx&printerType=1
        """
        if use_cache and self._printer_list_cache is not None:
            return self._printer_list_cache

        url = f"{self.api_base_url}/external_api/printer_list"
        params = {
            **self._device_params,
            "printerType": self.printer_type,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=self._headers)
            data = self._handle_response(resp)

        result = data.get("data", {})
        if isinstance(result, dict):
            printers = result.get("row", [])
        elif isinstance(result, list):
            printers = result
        else:
            printers = []

        if use_cache:
            self._printer_list_cache = printers

        logger.info(f"获取打印机列表成功，共 {len(printers)} 台")
        return printers

    async def get_printer_params(self, printer_model: str, use_cache: bool = True) -> dict:
        """
        获取打印机参数（调用后请保存缓存数据）
        GET /api/print/printer_params?printerModel=xxx
        """
        if use_cache and self._printer_params_cache is not None:
            return self._printer_params_cache

        url = f"{self.api_base_url}/print/printer_params"
        params = {"printerModel": printer_model}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=self._headers)
            data = self._handle_response(resp)

        result = data.get("data", {})

        if use_cache:
            self._printer_params_cache = result

        logger.info(f"获取打印机参数成功，型号: {printer_model}")
        return result

    def _detect_file_ext(self, file_url: str) -> str:
        """从 URL 自动检测文件后缀，用于 urlFileExt 参数"""
        from urllib.parse import urlparse, unquote
        import os

        parsed = urlparse(file_url)
        candidates = [unquote(parsed.path)]
        if parsed.query:
            from urllib.parse import parse_qs
            query = parse_qs(parsed.query)
            for key in ("filename", "file", "name", "key"):
                candidates.extend(query.get(key, []))

        valid_exts = (
            ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
            ".html", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".prn",
        )
        for candidate in candidates:
            _, ext = os.path.splitext(candidate.split("?")[0])
            if ext and ext.lower() in valid_exts:
                return ext.lower()
        return ".pdf"

    def _apply_optional_print_params(self, form_data: dict) -> None:
        optional_values = {
            "printerModel": self.printer_model,
            "targetIp": self.target_ip,
            "dmDefaultSource": self.dm_default_source,
            "dmMediaType": self.dm_media_type,
            "dmPrintQuality": self.dm_print_quality,
            "jpAutoAlign": self.jp_auto_align,
            "jpPageRange": self.jp_page_range,
            "htmlKernel": self.html_kernel,
            "errLimitNum": self.err_limit_num,
        }
        for key, value in optional_values.items():
            if value not in (None, ""):
                form_data[key] = str(value)

        form_data["reportDeviceStatus"] = "1" if self.report_device_status else "0"
        form_data["reportPrinterStatus"] = "1" if self.report_printer_status else "0"
        form_data["pdfRev"] = "1" if self.pdf_rev else "0"
        form_data["jpAutoRotate"] = "1" if self.jp_auto_rotate else "0"

    def _masked_form_data(self, form_data: dict) -> dict:
        safe = dict(form_data)
        if safe.get("deviceKey"):
            safe["deviceKey"] = "***"
        if safe.get("jobFile") and len(str(safe["jobFile"])) > 160:
            safe["jobFile"] = f"{str(safe['jobFile'])[:160]}..."
        return safe

    async def add_task(
        self,
        file_url: str,
        copies: int = 1,
        paper_size: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> dict:
        """
        第二步：提交打印任务（URL 方式）
        POST /api/print/job (form-data 格式，非 JSON)

        jobFile 支持链接地址（字符串格式），若使用链接需额外传 urlFileExt 参数

        Args:
            file_url: 待打印文件的 URL
            copies: 打印份数
            paper_size: 纸张尺寸（覆盖默认）
            callback_url: 回调 URL

        Returns:
            dict: 包含 task_id 等信息
        """
        url = f"{self.api_base_url}/print/job"

        # 自动检测 URL 文件后缀
        detected_ext = self._detect_file_ext(file_url)

        # 构建表单参数（按照官方文档 V3 API）
        form_data = {
            "deviceId": self.device_id,
            "deviceKey": self.device_key,
            "devicePort": self.device_port,
            # jobFile 传 URL 字符串
            "jobFile": file_url,
            "urlFileExt": detected_ext,
            # 打印参数
            "dmPaperSize": str(paper_size or self.dm_paper_size),
            "jpScale": self.jp_scale,
            "jpAutoScale": self.jp_auto_scale,
            "dmOrientation": self.dm_orientation,
            "dmCopies": str(copies or self.dm_copies),
            "dmColor": self.dm_color,
        }

        # 双面打印
        if self.dm_duplex:
            form_data["dmDuplex"] = self.dm_duplex
        self._apply_optional_print_params(form_data)

        # 自定义纸张尺寸（dmPaperSize=0 时需要）
        if form_data["dmPaperSize"] == "0":
            form_data["dmPaperWidth"] = str(self.dm_paper_width)
            form_data["dmPaperLength"] = str(self.dm_paper_length)

        # 回调 URL
        effective_callback_url = callback_url or self.callback_url
        if effective_callback_url:
            form_data["callbackUrl"] = effective_callback_url

        logger.info("提交蓝阔URL打印任务参数: %s", self._masked_form_data(form_data))
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=form_data, headers=self._headers)
            data = self._handle_response(resp)

        task_id = data.get("data", {}).get("task_id")
        if task_id:
            logger.info(f"打印任务已提交，task_id={task_id}")
        else:
            logger.warning(f"打印任务提交响应: {data}")

        return data.get("data", {})

    async def add_task_with_file(
        self,
        file_bytes: bytes,
        filename: str,
        copies: int = 1,
        paper_size: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> dict:
        """
        第二步：提交打印任务（文件上传方式）
        POST /api/print/job (form-data 格式)

        jobFile 为 formfile 格式时，参数需为文件上传

        Args:
            file_bytes: 文件二进制数据
            filename: 文件名（含扩展名）
            copies: 打印份数
            paper_size: 纸张尺寸
            callback_url: 回调 URL

        Returns:
            dict: 包含 task_id 等信息
        """
        url = f"{self.api_base_url}/print/job"

        form_data = {
            "deviceId": self.device_id,
            "deviceKey": self.device_key,
            "devicePort": self.device_port,
            "dmPaperSize": str(paper_size or self.dm_paper_size),
            "jpScale": self.jp_scale,
            "jpAutoScale": self.jp_auto_scale,
            "dmOrientation": self.dm_orientation,
            "dmCopies": str(copies or self.dm_copies),
            "dmColor": self.dm_color,
        }

        if self.dm_duplex:
            form_data["dmDuplex"] = self.dm_duplex
        self._apply_optional_print_params(form_data)

        if form_data["dmPaperSize"] == "0":
            form_data["dmPaperWidth"] = str(self.dm_paper_width)
            form_data["dmPaperLength"] = str(self.dm_paper_length)

        effective_callback_url = callback_url or self.callback_url
        if effective_callback_url:
            form_data["callbackUrl"] = effective_callback_url

        logger.info("提交蓝阔文件打印任务参数: %s", self._masked_form_data(form_data))
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                data=form_data,
                # jobFile 为文件上传字段
                files={"jobFile": (filename, file_bytes)},
                headers=self._headers,
            )
            data = self._handle_response(resp)

        task_id = data.get("data", {}).get("task_id")
        if task_id:
            logger.info(f"打印任务已提交（文件上传），task_id={task_id}")

        return data.get("data", {})

    async def get_task_status(self, task_id: str) -> dict:
        """
        查询打印任务状态
        GET /api/print/job?task_id=xxx

        Returns:
            dict: 包含 status 等信息
                status 值: 0=等待/排队, 1=正在打印, 2=打印完成, 3=打印失败
        """
        url = f"{self.api_base_url}/print/job"
        params = {
            **self._device_params,
            "task_id": task_id,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=self._headers)
            data = self._handle_response(resp)

        return data.get("data", {})

    async def cancel_task(self, task_id: str) -> dict:
        """
        取消打印任务
        DELETE /api/print/job
        """
        url = f"{self.api_base_url}/print/job"
        payload = {
            **self._device_params,
            "task_id": task_id,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(url, json=payload, headers=self._headers)
            data = self._handle_response(resp)

        return data.get("data", {})


def get_lankuo_config(db) -> Optional[dict]:
    """从数据库读取蓝阔云打印配置"""
    from app.models import SystemSettings
    import json

    setting = db.query(SystemSettings).filter(
        SystemSettings.key == "lankuo_print_config"
    ).first()
    if not setting or not setting.value:
        return None

    try:
        config = json.loads(setting.value)
        config.pop("urlFileExt", None)
        if config.get("enabled"):
            return config
    except Exception:
        pass

    return None


def _template_uses_activity_paper(template: dict) -> bool:
    if template.get("printConfigMode") == "activity":
        return True
    if template.get("activeTemplateId") or template.get("templates"):
        return True
    return bool(template.get("paperWidthMm") and template.get("paperHeightMm"))


def get_effective_lankuo_config(db, activity_id: Optional[int] = None) -> Optional[dict]:
    """读取当前应生效的蓝阔配置。

    默认使用系统设置里的全局云打印配置；活动打印模板只有在 printConfigMode=activity 时
    才覆盖纸张参数。画布编辑器尺寸不参与蓝阔纸张参数选择。
    """
    config = get_lankuo_config(db)
    if not config or not activity_id:
        return config

    from app.models import SystemSettings
    import json

    setting = db.query(SystemSettings).filter(
        SystemSettings.key == f"activity_{activity_id}_print_template"
    ).first()
    if not setting or not setting.value:
        config["_printConfigMode"] = "global"
        return config

    try:
        template = json.loads(setting.value)
    except Exception:
        config["_printConfigMode"] = "global"
        return config

    if not _template_uses_activity_paper(template):
        config["_printConfigMode"] = "global"
        return config

    effective = dict(config)
    dm_paper_size = str(template.get("dmPaperSize") or "").strip()
    if dm_paper_size:
        effective["dmPaperSize"] = dm_paper_size
    elif template.get("paperWidthMm") and template.get("paperHeightMm"):
        effective["dmPaperSize"] = "0"

    if effective.get("dmPaperSize") == "0":
        try:
            effective["dmPaperWidth"] = int(round(float(template.get("paperWidthMm", 0)) * 10))
            effective["dmPaperLength"] = int(round(float(template.get("paperHeightMm", 0)) * 10))
        except (TypeError, ValueError):
            pass

    effective["_printConfigMode"] = "activity"
    return effective
