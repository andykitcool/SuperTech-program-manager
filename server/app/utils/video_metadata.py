import logging
import httpx

logger = logging.getLogger(__name__)


def _parse_duration_tag(tag: str):
    """Parse a DURATION tag like '00:00:13.700000000' into seconds."""
    try:
        parts = tag.split(":")
        if len(parts) == 3:
            h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
            return round(h * 3600 + m * 60 + s, 1)
    except (ValueError, TypeError, IndexError):
        pass
    return None


async def extract_video_metadata(video_url: str) -> dict:
    """Extract duration and creation_time from a video URL via Qiniu avinfo API.

    Appends ``?avinfo`` to the video URL and parses the JSON response.
    Returns dict with keys: duration (float), creation_time (str or None).
    """
    try:
        separator = "?" if "?" not in video_url else "&"
        avinfo_url = f"{video_url}{separator}avinfo"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(avinfo_url)
            resp.raise_for_status()
            data = resp.json()

        # Duration — from format.duration
        duration = None
        if data.get("format", {}).get("duration"):
            try:
                duration = round(float(data["format"]["duration"]), 1)
            except (ValueError, TypeError):
                pass

        # Fallback: duration from video stream duration field
        if duration is None:
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video" and stream.get("duration"):
                    try:
                        duration = round(float(stream["duration"]), 1)
                        break
                    except (ValueError, TypeError):
                        pass

        # Fallback: duration from video stream DURATION tag (e.g. "00:00:13.700000000")
        if duration is None:
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    tag_dur = (stream.get("tags") or {}).get("DURATION", "")
                    if tag_dur:
                        duration = _parse_duration_tag(tag_dur)
                        if duration is not None:
                            break

        # Creation time — from format.tags.creation_time
        creation_time = None
        tags = data.get("format", {}).get("tags", {})
        if tags.get("creation_time"):
            creation_time = tags["creation_time"]

        # Fallback: creation_time from any stream tags
        if not creation_time:
            for stream in data.get("streams", []):
                stream_tags = stream.get("tags", {})
                if stream_tags.get("creation_time"):
                    creation_time = stream_tags["creation_time"]
                    break

        return {"duration": duration, "creation_time": creation_time}

    except Exception as e:
        logger.warning(f"Failed to extract video metadata via avinfo: {e}")
        return {}
