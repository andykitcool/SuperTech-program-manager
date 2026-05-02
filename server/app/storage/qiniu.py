import asyncio
from typing import Optional
from qiniu import Auth, put_data, BucketManager

from app.storage import BaseStorageAdapter


class QiniuAdapter(BaseStorageAdapter):

    def __init__(self, config: dict):
        self.access_key = config.get("access_key", "")
        self.secret_key = config.get("secret_key", "")
        self.bucket = config.get("bucket", "")
        self.domain = config.get("domain", "").rstrip("/")
        self._auth = None
        self._bucket_manager = None

    @property
    def provider_name(self) -> str:
        return "qiniu"

    def _get_auth(self) -> Auth:
        if self._auth is None:
            self._auth = Auth(self.access_key, self.secret_key)
        return self._auth

    def _get_bucket_manager(self) -> BucketManager:
        if self._bucket_manager is None:
            self._bucket_manager = BucketManager(self._get_auth())
        return self._bucket_manager

    def _get_url(self, key: str) -> str:
        if self.domain:
            domain = self.domain if self.domain.startswith("http") else f"https://{self.domain}"
            return f"{domain}/{key}"
        return f"https://{self.bucket}.clouddn.com/{key}"

    async def upload_file(self, data: bytes, key: str, content_type: Optional[str] = None) -> str:
        auth = self._get_auth()
        token = auth.upload_token(self.bucket, key)

        def _upload():
            ret, info = put_data(token, key, data)
            if info.status_code != 200:
                raise Exception(f"Qiniu upload failed: {info}")

        await asyncio.to_thread(_upload)
        return self._get_url(key)

    async def download_file(self, key: str) -> bytes:
        import httpx
        url = self._get_url(key)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            return resp.content

    async def delete_file(self, key: str) -> bool:
        bm = self._get_bucket_manager()
        await asyncio.to_thread(bm.delete, self.bucket, key)
        return True

    async def move_file(self, src_key: str, dest_key: str) -> bool:
        bm = self._get_bucket_manager()
        ret, info = await asyncio.to_thread(bm.move, self.bucket, src_key, self.bucket, dest_key)
        if info.status_code not in (200, 612):
            raise Exception(f"Qiniu move failed: {info}")
        return True

    async def generate_url(self, key: str, expires: int = 3600) -> str:
        auth = self._get_auth()
        base_url = self._get_url(key)
        url = await asyncio.to_thread(
            auth.private_download_url, base_url, expires=expires
        )
        return url

    def build_url(self, key: str) -> str:
        return self._get_url(key)

    def generate_upload_token(self, key: str, expires: int = 3600) -> str:
        """Generate a Qiniu upload token scoped to a specific key."""
        auth = self._get_auth()
        return auth.upload_token(self.bucket, key, expires)

    def get_video_thumbnail_url(self, video_url: str) -> Optional[str]:
        """Use Qiniu vframe API to extract a video frame as thumbnail."""
        if not video_url:
            return None
        if not video_url.startswith("http"):
            video_url = f"https://{video_url}"
        separator = "?" if "?" not in video_url else "&"
        return f"{video_url}{separator}vframe/jpg/offset/1/w/320/h/180"

    async def test_connection(self) -> bool:
        try:
            bm = self._get_bucket_manager()
            # stat a non-existent key: 612 = connected but file not found (expected), other errors = real failure
            ret, info = await asyncio.to_thread(
                lambda: bm.stat(self.bucket, "__test_connection__")
            )
            # 612 means "no such file" — connection is valid
            return info.status_code == 612
        except Exception:
            return False
