"""Server-side Fabric canvas rendering for print jobs."""

import base64
import copy
import json
import mimetypes
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


DEFAULT_LOCAL_BASE_URL = os.getenv("INTERNAL_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
FABRIC_VENDOR_PATH = Path(__file__).resolve().parents[1] / "static" / "vendor" / "fabric.min.js"
IMAGE_FETCH_TIMEOUT_SECONDS = 30
MAX_INLINE_IMAGE_BYTES = 25 * 1024 * 1024


@lru_cache(maxsize=1)
def _fabric_script() -> str:
    return FABRIC_VENDOR_PATH.read_text(encoding="utf-8")


def _normalize_asset_url(value: str, base_url: str) -> str:
    if value.startswith(("data:", "http://", "https://", "blob:")):
        return value
    if value.startswith("/"):
        return f"{base_url}{value}"
    if value.startswith("uploads/"):
        return f"{base_url}/{value}"
    return value


def _guess_image_content_type(url: str, header_value: str | None) -> str:
    if header_value:
        content_type = header_value.split(";", 1)[0].strip().lower()
        if content_type.startswith("image/"):
            return content_type
    guessed, _ = mimetypes.guess_type(urlparse(url).path)
    return guessed if guessed and guessed.startswith("image/") else "image/png"


@lru_cache(maxsize=256)
def _inline_image_url(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=IMAGE_FETCH_TIMEOUT_SECONDS) as response:
        content_type = _guess_image_content_type(url, response.headers.get("content-type"))
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_INLINE_IMAGE_BYTES:
            raise RuntimeError(f"Image is too large to inline: {url}")
        image_bytes = response.read(MAX_INLINE_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_INLINE_IMAGE_BYTES:
        raise RuntimeError(f"Image is too large to inline: {url}")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _prepare_image_src(value: str, base_url: str) -> str:
    normalized = _normalize_asset_url(value, base_url)
    if normalized.startswith("data:"):
        return normalized
    if normalized.startswith(("http://", "https://")):
        return _inline_image_url(normalized)
    return normalized


def _prepare_font_family(value: str) -> str:
    aliases = {
        "Noto Sans SC": "Noto Sans CJK SC",
        "Noto Serif SC": "Noto Serif CJK SC",
        "ZCOOL QingKe HuangYou": "Noto Sans CJK SC",
        "ZCOOL XiaoWei": "Noto Serif CJK SC",
    }
    return aliases.get(value, value)


def _prepare_fabric_json(value: Any, base_url: str) -> Any:
    if isinstance(value, list):
        return [_prepare_fabric_json(item, base_url) for item in value]
    if not isinstance(value, dict):
        return value

    result = {}
    for key, item in value.items():
        if key == "_canvas_image":
            continue
        if key == "src" and isinstance(item, str):
            result[key] = _prepare_image_src(item, base_url)
        elif key == "fontFamily" and isinstance(item, str):
            result[key] = _prepare_font_family(item)
        else:
            result[key] = _prepare_fabric_json(item, base_url)

    if result.get("type") in {"image", "Image"} and "crossOrigin" not in result:
        result["crossOrigin"] = "anonymous"
    return result


def _canvas_size(payload: dict) -> tuple[int, int]:
    width = payload.get("_canvas_width") or payload.get("width") or 1500
    height = payload.get("_canvas_height") or payload.get("height") or 1500
    try:
        width = int(float(width))
        height = int(float(height))
    except (TypeError, ValueError):
        width, height = 1500, 1500
    return max(1, min(width, 5000)), max(1, min(height, 5000))


def render_fabric_payload_to_png(
    payload: dict,
    *,
    multiplier: int = 1,
    base_url: str = DEFAULT_LOCAL_BASE_URL,
    timeout_ms: int = 60000,
) -> bytes:
    """Render a Fabric JSON payload to PNG bytes using headless Chromium."""
    payload_copy = copy.deepcopy(payload or {})
    width, height = _canvas_size(payload_copy)
    fabric_json = _prepare_fabric_json(payload_copy, base_url)
    multiplier = max(1, min(int(multiplier or 1), 4))

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <script>{_fabric_script()}</script>
  <style>
    html, body {{ margin: 0; padding: 0; background: transparent; }}
    canvas {{ display: block; }}
  </style>
</head>
<body>
  <div id="canvasHost"></div>
  <script>
    window.__payload = {json.dumps(fabric_json, ensure_ascii=False)};
    window.__renderPrintCanvas = async function() {{
      const fabricNS = window.fabric || window.Fabric;
      if (!fabricNS || !fabricNS.StaticCanvas) {{
        throw new Error('Fabric renderer not loaded');
      }}
      if (window.__printCanvas) {{
        window.__printCanvas.dispose();
      }}
      const host = document.getElementById('canvasHost');
      host.innerHTML = '<canvas></canvas>';
      const canvasElement = host.querySelector('canvas');
      const canvas = new fabricNS.StaticCanvas(canvasElement, {{
        width: {width},
        height: {height},
        renderOnAddRemove: false,
        enableRetinaScaling: false,
        backgroundColor: '#ffffff'
      }});
      window.__printCanvas = canvas;
      await canvas.loadFromJSON(window.__payload);
      if (document.fonts && document.fonts.ready) {{
        await document.fonts.ready;
      }}
      canvas.setDimensions({{ width: {width}, height: {height} }});
      canvas.setZoom(1);
      canvas.renderAll();
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return canvas.toDataURL({{
        format: 'png',
        quality: 1,
        multiplier: {multiplier}
      }});
    }};
  </script>
</body>
</html>
"""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(
                viewport={
                    "width": min(width, 2400),
                    "height": min(height, 2400),
                },
                device_scale_factor=1,
            )
            page.goto(f"{base_url}/api/health", wait_until="domcontentloaded", timeout=timeout_ms)
            page.set_content(html, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_function("window.fabric && window.__renderPrintCanvas", timeout=timeout_ms)
            data_url = page.evaluate("window.__renderPrintCanvas()")
        finally:
            browser.close()

    if not isinstance(data_url, str) or "," not in data_url:
        raise RuntimeError("Server renderer did not return a PNG data URL")
    header, body = data_url.split(",", 1)
    if "image/png" not in header:
        raise RuntimeError(f"Unexpected render output: {header[:80]}")
    return base64.b64decode(body)
