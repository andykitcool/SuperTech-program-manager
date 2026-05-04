import asyncio
import oss2
from typing import Optional

from app.storage import BaseStorageAdapter


class AliyunOSSAdapter(BaseStorageAdapter):

    def __init__(self, config: dict):
        self.access_key_id = config.get("access_key_id", "")
        self.access_key_secret = config.get("access_key_secret", "")
        self.bucket_name = config.get("bucket", "")
        self.endpoint = config.get("endpoint", "")
        self.region = config.get("region", "oss-cn-hangzhou")
        self._bucket = None

    @property
    def provider_name(self) -> str:
        return "aliyun"

    def _get_bucket(self) -> oss2.Bucket:
        if self._bucket is None:
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
        return self._bucket

    async def upload_file(self, data: bytes, key: str, content_type: Optional[str] = None) -> str:
        bucket = self._get_bucket()
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        await asyncio.to_thread(
            bucket.put_object, key, data, headers=headers if headers else None
        )
        return f"https://{self.bucket_name}.{self.endpoint}/{key}"

    async def download_file(self, key: str) -> bytes:
        bucket = self._get_bucket()
        result = await asyncio.to_thread(bucket.get_object, key)
        return result.read()

    async def delete_file(self, key: str) -> bool:
        bucket = self._get_bucket()
        await asyncio.to_thread(bucket.delete_object, key)
        return True

    async def generate_url(self, key: str, expires: int = 3600) -> str:
        bucket = self._get_bucket()
        url = await asyncio.to_thread(
            bucket.sign_url, "GET", key, expires
        )
        return url

    def build_url(self, key: str) -> str:
        return f"https://{self.bucket_name}.{self.endpoint}/{key}"

    async def test_connection(self) -> bool:
        try:
            bucket = self._get_bucket()
            await asyncio.to_thread(bucket.head_bucket)
            return True
        except Exception:
            return False
